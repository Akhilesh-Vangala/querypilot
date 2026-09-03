from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
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
        if message.get("role") == "user" and str(message.get("content", "")).startswith("Tool result:")
    )


class StubLLM:
    """Used when OPENAI_API_KEY is unset. Compiles SQL via intents.py."""

    def complete(self, messages: list[dict[str, str]]) -> str:
        question = _extract_question(messages)
        intent = classify(question)
        if intent is None:
            return json.dumps(
                {
                    "final": {
                        "answer": (
                            "I could not map that question onto a known warehouse metric. "
                            "Try asking about revenue, scrap, production, stockouts, or freight."
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
            return json.dumps({"tool": "describe_table", "args": {"name": intent.table}})
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
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def complete(self, messages: list[dict[str, str]]) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "messages": messages,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"openai request failed: {exc}") from exc
        text = body["choices"][0]["message"]["content"]
        return text.strip()


def get_llm() -> LLMClient:
    from ..config import get_settings

    settings = get_settings()
    key = (settings.openai_api_key or "").strip()
    if key:
        return OpenAILLM(key, settings.openai_model)
    return StubLLM()


def parse_action(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    return json.loads(text)
