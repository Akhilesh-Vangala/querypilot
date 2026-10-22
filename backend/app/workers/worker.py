"""Bounded separate query worker with leases and no automatic paid replay."""

import argparse
import json
import os
import signal
import threading
import time
from pathlib import Path
from sqlalchemy.orm import Session
from app.persistence import db
from app.persistence.runs import RunRepository
from app.persistence.runs import RunConflict
from app.agents.analytics.workflow import AnalyticsWorkflow
from app.agents.analytics.llm import StubLLM
from app.agents.analytics.llm import get_llm
from app.core.run_contract import run_scope


def stamp():
    path = Path(os.getenv("WORKER_HEARTBEAT_FILE", "/tmp/querypilot-worker-heartbeat"))
    path.write_text(str(os.getpid()))


def process_one(repository, stopped=None, identity=None):
    stopped = stopped or threading.Event()
    job = repository.claim(identity=identity)
    if not job:
        return False
    finished = threading.Event()

    def renewal():
        while not finished.wait(10):
            try:
                repository.heartbeat(job)
                stamp()
            except Exception:
                stopped.set()
                return

    thread = threading.Thread(target=renewal, daemon=True)
    thread.start()

    def progress(event):
        if stopped.is_set():
            raise RunConflict("Worker is shutting down")
        repository.event(job, event)

    try:
        with Session(repository.engine) as session:
            client = (
                StubLLM() if job.get("mode", "baseline") == "baseline" else get_llm()
            )
            if job.get("mode") == "live" and isinstance(client, StubLLM):
                raise RuntimeError(
                    "Live investigator is unavailable in this worker; no fallback"
                )
            with run_scope(job["id"]):
                workflow = AnalyticsWorkflow(session, llm=client, progress=progress)
            try:
                result = workflow.run(job["question"])
            finally:
                close = getattr(workflow.llm, "close", None)
                if close:
                    close()
        if stopped.is_set():
            raise RunConflict("Worker is shutting down")
        repository.finish(job, result=result)
    except BaseException as error:
        try:
            repository.finish(
                job,
                error="WorkerShutdown" if stopped.is_set() else type(error).__name__,
            )
        except RunConflict:
            pass
    finally:
        finished.set()
        thread.join(timeout=2)
    return True


def health():
    path = Path(os.getenv("WORKER_HEARTBEAT_FILE", "/tmp/querypilot-worker-heartbeat"))
    try:
        if time.time() - path.stat().st_mtime > 35:
            raise ValueError()
        os.kill(int(path.read_text()), 0)
    except (OSError, ValueError):
        raise SystemExit(1) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--health", action="store_true")
    args = parser.parse_args()
    if args.health:
        return health()
    if db.warehouse_engine is not None and db.engine.dialect.name == "postgresql":
        from app.core.production_checks import verify_warehouse_role

        verify_warehouse_role(db.warehouse_engine)
    repository = RunRepository(db.engine)
    if args.once:
        return process_one(repository)
    stopped = threading.Event()
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: stopped.set())
    while not stopped.is_set():
        stamp()
        if not process_one(repository, stopped):
            stopped.wait(0.5)


if __name__ == "__main__":
    main()
