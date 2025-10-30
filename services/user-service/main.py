import os
import uvicorn
import logging
from fastapi import FastAPI, HTTPException

# --- OpenTelemetry (OTel) Imports ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Auto-instrumentation libraries
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# --- Globals ---
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

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

    # 1. Define a "Resource" for this service
    resource = Resource(attributes={
        "service.name": "user-service"
    })

    # 2. Configure the OTLP Exporter
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True
    )

    # 3. Set up the TracerProvider
    tracer_provider = TracerProvider(resource=resource)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

    # 4. Apply auto-instrumentation
    FastAPIInstrumentor.instrument_app(fastapi_app, tracer_provider=tracer_provider)

    logger.info(f"OpenTelemetry setup complete. Sending to: {otlp_endpoint}")

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
            logger.warning(f"User not found: {user_id}")
            span.set_attribute("error", True)
            span.set_attribute("user.found", False)
            # This exception will be automatically recorded by the OTel instrumentation
            raise HTTPException(status_code=404, detail="User not found")

        logger.info(f"User found: {user['username']}")
        span.set_attribute("user.found", True)
        span.set_attribute("user.username", user['username'])
        return user

# --- Run the App (for local testing) ---
if __name__ == "__main__":
    # Run on port 8001 to avoid conflicting with the api-gateway (8000)
    uvicorn.run(app, host="0.0.0.0", port=8001)
