"""
core/observability.py — OpenTelemetry initialisation for activia-trace.

Instruments the FastAPI application so that each incoming HTTP request
generates a span.  The instrumentation is:
  - Opt-in via the OTEL_ENABLED env var (default: False).
  - Independent of any specific exporter backend: the app starts normally
    even when no OTLP endpoint is configured.

Implemented: C-01 (foundation-setup)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def init_observability(app, *, enabled: bool = False, service_name: str = "activia-trace") -> None:
    """Instrument *app* with OpenTelemetry if *enabled* is True.

    Args:
        app:          The FastAPI application instance.
        enabled:      Whether to activate OTel instrumentation.
        service_name: Service name reported in traces.

    If *enabled* is False, this function is a no-op (the app starts
    without any tracing overhead).

    If *enabled* is True but OTel packages are not installed, a warning
    is logged and the app continues without instrumentation — startup
    is never blocked by a missing telemetry backend.
    """
    if not enabled:
        logger.debug("OpenTelemetry instrumentation is disabled (OTEL_ENABLED=false)")
        return

    try:
        from opentelemetry import trace  # noqa: PLC0415
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: PLC0415
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # noqa: PLC0415
        from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # Instrument FastAPI — every HTTP request becomes a span.
        # No exporter is registered here; add one in deployment config
        # (e.g. OTLPSpanExporter pointed at OTEL_EXPORTER_OTLP_ENDPOINT).
        FastAPIInstrumentor.instrument_app(app)

        logger.info("OpenTelemetry instrumentation enabled", extra={"service": service_name})

    except ImportError:
        logger.warning(
            "opentelemetry packages not found — instrumentation skipped. "
            "Install opentelemetry-sdk and opentelemetry-instrumentation-fastapi "
            "to enable tracing."
        )
