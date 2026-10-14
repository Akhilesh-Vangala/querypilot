from __future__ import annotations

import json
import re
from typing import Any, Protocol

from .intents import classify


class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> str: ...


def _extract_question(messages: list[dict[str, str]]) -> str:
    for message in messages:
        if message.get("role") != "user":
            continue
        content = message.get("content", "")
        if content.startswith("SQL error:") or content.startswith("Tool result:"):
            continue
        if "Question:" in content:
            return content.split("Question:", 1)[1].strip()
        return content.strip()
    return ""


def _tool_result_count(messages: list[dict[str, str]]) -> int:
    return sum(
        1
        for message in messages
        if message.get("role") == "user"
        and str(message.get("content", "")).startswith("Tool result:")
    )


class StubLLM:
    """Explicit deterministic development baseline. Compiles SQL via intents.py."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        question = _extract_question(messages)
        from .semantic import guided_comparison
        from pydantic import ValidationError

        try:
            comparison = guided_comparison(question)
        except (ValidationError, ValueError):
            return json.dumps(
                {
                    "final": {
                        "answer": "Specify a supported metric/dimension and valid nonoverlapping calendar windows, baseline first.",
                        "sql": "",
                        "chart": "table",
                        "refused": False,
                    }
                }
            )
        if comparison:
            return json.dumps(
                {"tool": "compare_metric", "args": comparison.model_dump()}
            )
        # Do not let the legacy Q1/claims classifier silently drop comparison scope.
        if any(
            word in question.lower()
            for word in ("compare", "versus", "between q", "explains the change")
        ):
            return json.dumps(
                {
                    "final": {
                        "answer": "Use the Compare periods page to choose a reviewed metric, dimension and explicit dates. Guided mode only accepts its exact comparison templates; flexible questions require a configured live investigator.",
                        "sql": "",
                        "chart": "table",
                        "refused": False,
                    }
                }
            )
        intent = classify(question)
        if intent is None:
            return json.dumps(
                {
                    "final": {
                        "answer": (
                            "I could not map that question onto a known warehouse metric. "
                            "Try asking about claims, declined referrals, closed panels, or care coordination."
                        ),
                        "sql": "",
                        "chart": "table",
                        "refused": False,
                    }
                }
            )
        if intent.refused:
            return json.dumps(
                {
                    "final": {
                        "answer": intent.answer,
                        "sql": "",
                        "chart": "table",
                        "refused": True,
                    }
                }
            )

        seen = _tool_result_count(messages)
        if seen == 0:
            return json.dumps({"tool": "list_tables", "args": {}})
        if seen == 1:
            return json.dumps(
                {"tool": "describe_table", "args": {"name": intent.table}}
            )
        return json.dumps(
            {
                "final": {
                    "answer": intent.answer,
                    "sql": intent.sql,
                    "chart": intent.chart,
                    "refused": False,
                }
            }
        )


class OpenAILLM:
    """Official SDK function calls; no generation retry or prompt persistence."""

    mode = "live"

    def __init__(self, api_key: str, model: str, client=None) -> None:
        from openai import OpenAI

        self.model = model
        self.client = client or OpenAI(api_key=api_key, timeout=30, max_retries=0)
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.requests = 0
        self.history = []
        self.seen_messages = 0
        self.pending_call_id = None
        self.last_action = None

    def complete(self, messages: list[dict[str, str]]) -> str:
        from ..config import get_settings
        from .protocol import tool_definitions

        settings = get_settings()
        if self.pending_call_id is None:
            native_input = list(messages)
        else:
            # Correlate actual provider calls/results by call_id. Never replay a
            # tool result as a new user instruction or drop reasoning items.
            if (
                len(messages) != self.seen_messages + 2
                or messages[-2] != {"role": "assistant", "content": self.last_action}
                or messages[-1].get("role") != "user"
                or not messages[-1].get("content", "").startswith("Tool result: ")
            ):
                raise RuntimeError(
                    "Model/tool transcript does not match the pending call"
                )
            native_input = self.history + [
                {
                    "type": "function_call_output",
                    "call_id": self.pending_call_id,
                    "output": messages[-1]["content"][len("Tool result: ") :],
                }
            ]
        if len(json.dumps(native_input)) > settings.max_prompt_chars:
            raise RuntimeError("Model context budget exceeded")
        if (
            self.requests >= settings.max_model_rounds
            or sum(self.usage.values()) >= settings.max_run_tokens
        ):
            raise RuntimeError("Model run budget exceeded")
        self.requests += 1
        response = self.client.responses.create(
            model=self.model,
            input=native_input,
            tools=tool_definitions(),
            tool_choice="required",
            parallel_tool_calls=False,
            max_output_tokens=settings.max_output_tokens,
            store=False,
        )
        usage = response.usage
        if usage:
            self.usage["input_tokens"] += usage.input_tokens
            self.usage["output_tokens"] += usage.output_tokens
        if (
            response.status != "completed"
            or sum(self.usage.values()) > settings.max_run_tokens
        ):
            raise RuntimeError(
                "Incomplete or over-budget model response; no automatic replay"
            )
        calls = [item for item in response.output if item.type == "function_call"]
        if len(calls) != 1:
            raise RuntimeError("Exactly one typed model action is required")
        call = calls[0]
        arguments = json.loads(call.arguments)
        self.history = native_input + [
            item.model_dump(exclude_none=True) for item in response.output
        ]
        self.pending_call_id = call.call_id
        self.seen_messages = len(messages)
        if call.name == "finish":
            self.last_action = json.dumps({"final": arguments})
        else:
            self.last_action = json.dumps({"tool": call.name, "args": arguments})
        return self.last_action

    def close(self):
        self.client.close()


def get_llm() -> LLMClient:
    from ..config import get_settings

    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    if key and settings.allow_live_ai:
        return OpenAILLM(key, settings.openai_model)
    return StubLLM()


def parse_action(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)
