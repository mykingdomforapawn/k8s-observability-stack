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
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Auto-instrumentation libraries
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# --- Globals ---
logger = logging.getLogger(__name__)

# OTel Tracing Globals
tracer = trace.get_tracer(__name__)

# OTel Metrics Globals
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
def setup_opentelemetry(fastapi_app: FastAPI):
    """
    Configures OpenTelemetry instrumentation for the app.
    """

    # Define a "Resource" for this service
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

    # 3. Apply auto-instrumentation
    FastAPIInstrumentor.instrument_app(fastapi_app)

    logger.info(f"OpenTelemetry (Traces & Metrics) setup complete. Sending to: {otlp_endpoint}")

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
    # The auto-instrumentation will automatically create a "parent" span
    # from the incoming request (which has the trace context from the api-gateway).
    # This manual span will be a "child" of that.
    with tracer.start_as_current_span("find_user_in_db") as span:

        logger.info(f"Looking up user_id: {user_id}")
        span.set_attribute("user.id", user_id)

        user = FAKE_DB.get(user_id)

        if not user:
            # Add 1 to our counter, with an attribute for "found=false"
            db_lookup_counter.add(1, {"user.found": "false"})

            logger.warning(f"User not found: {user_id}")
            span.set_attribute("error", True)
            span.set_attribute("user.found", False)
            raise HTTPException(status_code=404, detail="User not found")

        # Add 1 to our counter, with an attribute for "found=true"
        db_lookup_counter.add(1, {"user.found": "true"})

        logger.info(f"User found: {user['username']}")
        span.set_attribute("user.found", True)
        span.set_attribute("user.username", user['username'])
        return user

# --- Run the App (for local testing) ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
