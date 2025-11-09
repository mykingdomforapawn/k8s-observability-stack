import os
import httpx
import uvicorn
import logging
from fastapi import FastAPI

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
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# --- Globals ---
logger = logging.getLogger(__name__)

# OTel Tracing Globals
tracer = trace.get_tracer(__name__)

# OTel Metrics Globals
meter = metrics.get_meter(__name__)
user_requests_counter = meter.create_counter(
    name="api.user.requests",
    unit="1",
    description="Counts the number of requests to the /user endpoint"
)

# --- OTel Setup Function ---
def setup_opentelemetry(fastapi_app: FastAPI):
    """
    Configures OpenTelemetry instrumentation for the app.
    """

    # Define a "Resource" for this service (applies to BOTH traces and metrics)
    resource = Resource(attributes={
        "service.name": "api-gateway"
    })

    # Get the OTel Collector endpoint from environment variables
    # This must be the gRPC endpoint (no http://)
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

    # 4. Apply auto-instrumentation
    FastAPIInstrumentor.instrument_app(fastapi_app)
    HTTPXClientInstrumentor().instrument()

    logger.info(f"OpenTelemetry (Traces & Metrics) setup complete. Sending to: {otlp_endpoint}")

# --- FastAPI App Creation ---
app = FastAPI()

# --- OTel Setup ---
setup_opentelemetry(app)

# --- API Endpoints ---
@app.get("/user/{user_id}")
async def get_user(user_id: str):
    """
    Main endpoint. It calls the user-service to get data.
    """

    # Add an attribute (label) for the user_id
    user_requests_counter.add(1, {"user.id.path": user_id})

    # Manually create a new "span" for this specific operation
    with tracer.start_as_current_span("get_user_handler") as span:
        logger.info(f"Request received for user_id: {user_id}")
        span.set_attribute("user.id", user_id)

        try:
            user_service_url = os.getenv("USER_SERVICE_URL", "http://localhost:8001")

            async with httpx.AsyncClient() as client:
                response = await client.get(f"{user_service_url}/internal/user/{user_id}")

            response.raise_for_status()
            user_data = response.json()

            span.set_attribute("http.status_code", response.status_code)
            return user_data

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling user-service: {e}")
            span.set_attribute("http.status_code", e.response.status_code)
            return {"error": "Failed to retrieve user data", "status": e.response.status_code}
        except Exception as e:
            logger.error(f"Error calling user-service: {e}")
            span.set_attribute("error", True)
            return {"error": "Internal server error"}

# --- Run the App (for local testing) ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
