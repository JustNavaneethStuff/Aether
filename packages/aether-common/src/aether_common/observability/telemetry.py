import os
import uuid
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["service", "method", "endpoint", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["service", "method", "endpoint"],
)
AGENT_EXECUTIONS = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution duration",
    ["agent_name"],
)
LLM_TOKENS = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["provider", "model", "type"],
)
LLM_COST_USD = Counter(
    "llm_cost_usd_total",
    "Total LLM cost in USD",
    ["provider", "model"],
)
EVALUATION_SCORE = Histogram(
    "evaluation_score",
    "Workflow evaluation scores",
    ["passed"],
)
APPROVAL_REQUESTS = Counter(
    "approval_requests_total",
    "Total approval requests",
    ["decision"],
)
WORKFLOW_PAUSE_DURATION = Histogram(
    "workflow_pause_duration_seconds",
    "Workflow pause duration awaiting approval",
)
EXPERIMENT_VARIANT_REQUESTS = Counter(
    "experiment_variant_requests_total",
    "Requests per experiment variant",
    ["experiment", "variant"],
)


def setup_logging(service_name: str, log_level: str = "INFO", log_format: str = "json") -> None:
    import logging

    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper(), logging.INFO)),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service_name)


def setup_tracing(service_name: str) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def instrument_fastapi(app: Any) -> None:
    FastAPIInstrumentor.instrument_app(app)


def get_metrics() -> bytes:
    return generate_latest()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
