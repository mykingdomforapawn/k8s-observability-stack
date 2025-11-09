import os
import uvicorn
import logging
from fastapi import FastAPI, HTTPException

# --- OpenTelemetry (OTel) Imports ---
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Metrics Imports
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Logging Imports (using protected members for beta API)
# noinspection PyProtectedMember
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
# noinspection PyProtectedMember
from opentelemetry._logs import set_logger_provider
# noinspection PyProtectedMember
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
# noinspection PyProtectedMember
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Auto-instrumentation libraries
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# --- Globals ---
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

db_lookup_counter = meter.create_counter(
    name="db.user.lookups",
    unit="1",
    description="Counts the number of user lookups"
)

# A fake "database" of users
FAKE_DB = {
    "123": {"id": "123", "username": "otelfan", "email": "otel@example.com"},
    "456": {"id": "456", "username": "tracing_rocks", "email": "trace@example.com"},
}

# --- OTel Setup Function ---
def setup_opentelemetry(app_to_instrument: FastAPI):
    """
    Configures OpenTelemetry instrumentation for the app.
    """

    resource = Resource(attributes={
        "service.name": "user-service"
    })

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317")

    # --- 1. Set up TRACES ---
    trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    # --- 2. Set up METRICS ---
    metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # --- 3. Set up LOGS ---
    log_exporter = OTLPLogExporter(endpoint=otlp_endpoint, insecure=True)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    set_logger_provider(logger_provider)

    handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    LoggingInstrumentor().instrument(
        set_logging_format=True,
        tracer_provider=tracer_provider,
        log_level=logging.INFO
    )

    # --- 4. Apply auto-instrumentation ---
    FastAPIInstrumentor.instrument_app(
        app_to_instrument,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider
    )

    logger.info(f"OpenTelemetry (Traces, Metrics, & Logs) setup complete. Sending to: {otlp_endpoint}")

# --- FastAPI App Creation ---
app = FastAPI()

# --- OTel Setup ---
setup_opentelemetry(app)

# --- API Endpoints ---
@app.get("/internal/user/{user_id}")
async def get_user_internal(user_id: str):
    """
    Internal endpoint to retrieve user data.
    """
    with tracer.start_as_current_span("find_user_in_db") as span:

        logger.info(f"Looking up user_id: {user_id}")
        span.set_attribute("user.id", user_id)

        user = FAKE_DB.get(user_id)

        if not user:
            db_lookup_counter.add(1, {"user.found": "false"})
            logger.warning(f"User not found: {user_id}")
            span.set_attribute("error", True)
            span.set_attribute("user.found", False)
            raise HTTPException(status_code=404, detail="User not found")

        db_lookup_counter.add(1, {"user.found": "true"})
        logger.info(f"User found: {user['username']}")
        span.set_attribute("user.found", True)
        span.set_attribute("user.username", user['username'])
        return user

# --- Run the App (for local testing) ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
