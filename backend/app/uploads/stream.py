"""Observed verification stages over SSE; no synthetic percentages or background jobs."""
import asyncio
import json
import threading
import time

from fastapi.responses import StreamingResponse

from .ingestion import UploadProblem
from .service import run
from .signing import attest


def stream(upload, finish=None):
    async def events():
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue(maxsize=32)
        stopped = threading.Event()
        started = time.monotonic()

        def emit(kind, data):
            if not stopped.is_set():
                try:
                    loop.call_soon_threadsafe(queue.put_nowait, (kind, data))
                except RuntimeError:
                    pass

        def execute():
            def progress(stage, state):
                emit("stage", {"stage": stage, "state": state, "elapsed_ms": round((time.monotonic()-started)*1000)})
            try:
                result = run(upload, progress=progress)
                result["elapsed_ms"] = round((time.monotonic()-started)*1000)
                emit("result", (finish or attest)(result))
            except UploadProblem as error:
                emit("problem", error.response())
            except ValueError as error:
                emit("problem", {"detail": str(error), "issues": [], "hint": "Review the selected rules and try again."})
            except Exception:
                emit("problem", {"detail": "Verification could not complete. No result was published.", "issues": [], "hint": "Try again, or export your draft and return later."})

        future = loop.run_in_executor(None, execute)
        try:
            while True:
                try:
                    kind, value = await asyncio.wait_for(queue.get(), timeout=5)
                except TimeoutError:
                    yield ": still connected\n\n"
                    continue
                yield "event: " + kind + "\ndata: " + json.dumps(value, separators=(",", ":")) + "\n\n"
                if kind in ("result", "problem"):
                    break
            await future
        finally:
            stopped.set()
            # Cancelling the waiting browser does not claim to kill a running
            # thread; its read-only, row-bounded calculation may finish.
            future.cancel()

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
