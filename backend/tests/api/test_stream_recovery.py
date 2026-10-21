"""Fault injection for actual asynchronous SSE delivery; no provider calls."""
import asyncio
import json
import threading
import unittest
from unittest.mock import patch
from app.uploads import stream as runtime


class StreamRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def collect(self, response):
        return [chunk async for chunk in response.body_iterator]

    async def test_progress_overflow_retains_terminal_result_without_loop_errors(self):
        errors=[]
        loop=asyncio.get_running_loop(); old=loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: errors.append(context))
        self.addCleanup(loop.set_exception_handler, old)
        def run(_, progress):
            for n in range(1000): progress(str(n), "complete")
            return {"verified": True}
        with patch.object(runtime, "run", run):
            chunks=await asyncio.wait_for(self.collect(runtime.stream(None, finish=lambda x:x)), 2)
        self.assertTrue(chunks[-1].startswith("event: result"))
        self.assertIn('"verified":true', chunks[-1])
        self.assertEqual(sum(c.startswith("event: result") for c in chunks),1)
        await asyncio.sleep(0)
        self.assertEqual(errors,[])

    async def test_mailbox_bounds_progress_and_never_overwrites_terminal(self):
        box=runtime._Mailbox(asyncio.get_running_loop())
        for n in range(1000): box.publish("stage", n)
        box.publish("result", {"verified":True});box.publish("problem",{})
        self.assertEqual(len(box.progress),32)
        self.assertEqual(box.take(),("stage",968))
        for n in range(31): box.take()
        self.assertEqual(box.take(),("result",{"verified":True}))
        box.close();box.publish("stage",1001);self.assertIsNone(box.take())

    async def test_worker_failure_after_progress_ends_with_safe_problem(self):
        def run(_,progress):
            for n in range(1000): progress(str(n),"complete")
            raise RuntimeError("sensitive internal payload")
        with patch.object(runtime,"run",run):
            chunks=await asyncio.wait_for(self.collect(runtime.stream(None)),2)
        self.assertTrue(chunks[-1].startswith("event: problem"))
        self.assertNotIn("sensitive", "".join(chunks))
        self.assertFalse(any(c.startswith("event: result") for c in chunks))

    async def test_deadline_ends_stream_without_publishing_late_result(self):
        started=threading.Event();release=threading.Event();finished=threading.Event();signed=[]
        def run(_,progress):
            started.set()
            try: release.wait(2); return {"verified":True}
            finally: finished.set()
        try:
            with patch.object(runtime,"run",run),patch.object(runtime,"STREAM_DEADLINE_SECONDS",.03):
                chunks=await asyncio.wait_for(self.collect(runtime.stream(None,finish=lambda v:signed.append(v))),1)
            self.assertTrue(started.is_set())
            self.assertIn("time limit",chunks[-1]);self.assertFalse(any(c.startswith("event: result") for c in chunks))
            release.set();self.assertTrue(await asyncio.to_thread(finished.wait,1))
            await asyncio.sleep(.01);self.assertEqual(signed,[])
        finally: release.set()

    async def test_disconnected_consumer_does_not_sign_late_result(self):
        release=threading.Event();finished=threading.Event();signed=[]
        def run(_,progress):
            progress("profile","complete")
            try: release.wait(2);return {"verified":True}
            finally:finished.set()
        try:
            with patch.object(runtime,"run",run):
                iterator=runtime.stream(None,finish=lambda v:signed.append(v)).body_iterator
                self.assertIn("event: stage",await asyncio.wait_for(anext(iterator),1))
                await iterator.aclose()
            release.set();self.assertTrue(await asyncio.to_thread(finished.wait,1))
            await asyncio.sleep(.01);self.assertEqual(signed,[])
        finally:release.set()
