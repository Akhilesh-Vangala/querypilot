"""Bounded observed SSE progress; terminal results cannot be lost to backpressure."""
import asyncio
from collections import deque
import json
import threading
import time

from fastapi.responses import StreamingResponse
from .ingestion import UploadProblem
from .service import run
from .signing import attest

STREAM_DEADLINE_SECONDS = 25.0


class _Mailbox:
    """Keep recent progress and a separate terminal slot; coalesce loop wakeups."""
    def __init__(self, loop):
        self.loop = loop
        self.wake = asyncio.Event()
        self.lock = threading.Lock()
        self.progress = deque(maxlen=32)
        self.terminal = None
        self.closed = False
        self.scheduled = False

    def publish(self, kind, value):
        with self.lock:
            if self.closed or self.terminal is not None:
                return
            if kind in ("result", "problem"):
                self.terminal = (kind, value)
            else:
                self.progress.append((kind, value))
            if self.scheduled:
                return
            self.scheduled = True
        try:
            self.loop.call_soon_threadsafe(self._notify)
        except RuntimeError:
            self.close()

    def _notify(self):
        with self.lock:
            self.scheduled = False
        self.wake.set()

    def take(self):
        with self.lock:
            if self.progress:
                return self.progress.popleft()
            return self.terminal

    def close(self):
        with self.lock:
            self.closed = True
            self.progress.clear()
            self.terminal = None


def stream(upload, finish=None):
    async def events():
        loop = asyncio.get_running_loop()
        mailbox = _Mailbox(loop)
        stopped = threading.Event()
        started = time.monotonic()

        def execute():
            def progress(stage, state):
                if not stopped.is_set():
                    mailbox.publish("stage", {"stage": stage, "state": state,
                        "elapsed_ms": round((time.monotonic()-started)*1000)})
            try:
                result = run(upload, progress=progress)
                if stopped.is_set():
                    return
                result["elapsed_ms"] = round((time.monotonic()-started)*1000)
                mailbox.publish("result", (finish or attest)(result))
            except UploadProblem as error:
                mailbox.publish("problem", error.response())
            except ValueError as error:
                mailbox.publish("problem", {"detail": str(error), "issues": [],
                    "hint": "Review the selected rules and try again."})
            except Exception:
                mailbox.publish("problem", {"detail": "Verification could not complete. No result was published.",
                    "issues": [], "hint": "Try again, or export your draft and return later."})

        future = loop.run_in_executor(None, execute)
        try:
            while True:
                remaining = STREAM_DEADLINE_SECONDS - (time.monotonic()-started)
                if remaining <= 0:
                    # Close before yielding: a slow consumer may suspend here.
                    stopped.set()
                    mailbox.close()
                    kind, value = "problem", {"detail": "Verification exceeded the request time limit. No result was published.",
                        "issues": [], "hint": "Use a smaller export or retry. Your source and rules remain available."}
                else:
                    # Clear before inspecting shared state so a producer notification
                    # between take() and wait() cannot be lost.
                    mailbox.wake.clear()
                    item = mailbox.take()
                    if item is None:
                        try:
                            await asyncio.wait_for(mailbox.wake.wait(), timeout=min(5, remaining))
                        except TimeoutError:
                            if time.monotonic()-started < STREAM_DEADLINE_SECONDS:
                                yield ": still connected\n\n"
                        continue
                    kind, value = item
                yield "event: " + kind + "\ndata: " + json.dumps(value, separators=(",", ":")) + "\n\n"
                if kind in ("result", "problem"):
                    break
        finally:
            stopped.set()
            mailbox.close()
            # A bounded read-only calculation already running in a thread may
            # finish. Cancellation/deadline does not claim to kill that thread.
            future.cancel()

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-store", "X-Accel-Buffering": "no"})
