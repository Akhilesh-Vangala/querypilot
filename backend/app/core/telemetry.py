"""OTLP tracing opt-in. Never export questions, SQL, rows, credentials or exception text."""

import os
import threading
from contextlib import contextmanager
from opentelemetry import trace

_lock = threading.Lock()
_configured = False


def configure():
    global _configured
    if _configured:
        return
    with _lock:
        if _configured:
            return
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        if endpoint:
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider = TracerProvider(
                resource=Resource.create(
                    {"service.name": os.getenv("OTEL_SERVICE_NAME", "querypilot")}
                )
            )
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            trace.set_tracer_provider(provider)
        _configured = True


@contextmanager
def span(name, **attributes):
    configure()
    with trace.get_tracer("querypilot").start_as_current_span(
        name,
        attributes=attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as current:
        try:
            yield current
        except BaseException as error:
            current.set_attribute("error.kind", type(error).__name__)
            current.set_status(trace.Status(trace.StatusCode.ERROR))
            raise
