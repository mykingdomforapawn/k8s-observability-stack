import os
import httpx
import uvicorn
import logging
from fastapi import FastAPI

# --- OpenTelemetry (OTel) Imports ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Auto-instrumentation libraries
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# --- Globals ---
# Set up a logger and a tracer for this service
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# --- OTel Setup Function ---
def setup_opentelemetry(fastapi_app: FastAPI):
    """
    Configures OpenTelemetry instrumentation for the app.
    """

    # 1. Define a "Resource" for this service
    resource = Resource(attributes={
        "service.name": "api-gateway"
    })

    # 2. Configure the OTLP Exporter
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True  # Use insecure (http) for local dev
    )

    # 3. Set up the TracerProvider
    tracer_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    # 4. Apply auto-instrumentation
    FastAPIInstrumentor.instrument_app(fastapi_app, tracer_provider=tracer_provider) # FIX 1
    HTTPXClientInstrumentor().instrument()

    logger.info(f"OpenTelemetry setup complete. Sending to: {otlp_endpoint}")

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

    # The 'tracer' object is created from the global OTel setup
    # Manually create a new "span" for this specific operation
    with tracer.start_as_current_span("get_user_handler") as span:

        logger.info(f"Request received for user_id: {user_id}") # FIX 2

        # Add attributes to the span for better debugging
        span.set_attribute("user.id", user_id) # FIX 2

        # Call the user-service and create a "child span" under "get_user_handler" span
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
