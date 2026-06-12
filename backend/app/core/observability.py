"""OpenTelemetry initialisation for activia-trace.

Configurable by environment (no exporter mandatory — the app
starts even without an OTLP endpoint configured).

Usage:
    from app.core.observability import setup_observability
    setup_observability()
"""

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.core.config import get_settings


def setup_observability(
    instrument_fastapi_app: object | None = None,
) -> None:
    """Initialise OpenTelemetry SDK and (optionally) instrument a FastAPI app.

    If ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set in ``Settings`` the
    exporter is configured accordingly; otherwise spans are printed
    to the console via ``ConsoleSpanExporter`` for local development.
    """
    settings = get_settings()

    resource = Resource.create({
        "service.name": settings.OTEL_SERVICE_NAME or "activia-trace",
    })

    provider = TracerProvider(resource=resource)

    # If no OTLP endpoint is configured, fall back to console exporter
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        # Deferred import – OTLP exporter is an optional dependency
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore[import-untyped,unused-ignore]
                OTLPSpanExporter,
            )
            exporter = OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            )
        except ImportError:
            exporter = ConsoleSpanExporter()
    else:
        exporter = ConsoleSpanExporter()

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    if instrument_fastapi_app is not None:
        FastAPIInstrumentor.instrument_app(instrument_fastapi_app)
