from flask import Flask, jsonify
from prometheus_client import Counter, Gauge, Histogram, make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

import logging
import random
import time
import os

# OpenTelemetry imports
from opentelemetry import trace

from opentelemetry.sdk.resources import Resource

from opentelemetry.sdk.trace import TracerProvider

from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor
)

from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter
)

from opentelemetry.instrumentation.flask import FlaskInstrumentor


app = Flask(__name__)


# ------------------------------------------------
# Logging
# ------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s level=%(levelname)s message=%(message)s"
)


# ------------------------------------------------
# OpenTelemetry / Tempo configuration
# ------------------------------------------------

resource = Resource.create({
    "service.name": "vehicle-dashboard"
})

tracer_provider = TracerProvider(
    resource=resource
)

trace.set_tracer_provider(
    tracer_provider
)


# Alloy will receive traces from Flask.
# We will configure Alloy to forward them to Tempo.

otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://alloy.monitoring.svc.cluster.local.:4318/v1/traces"
    )
)


span_processor = BatchSpanProcessor(
    otlp_exporter
)

tracer_provider.add_span_processor(
    span_processor
)


# Automatically create traces for Flask requests

FlaskInstrumentor().instrument_app(app)


# ------------------------------------------------
# Prometheus metrics
# ------------------------------------------------

REQUEST_COUNT = Counter(
    "vehicle_dashboard_requests_total",
    "Total requests received by the Vehicle Dashboard",
    ["endpoint"]
)


REQUEST_DURATION = Histogram(
    "vehicle_dashboard_request_duration_seconds",
    "Time taken to process Vehicle Dashboard requests",
    ["endpoint"]
)


VEHICLE_SPEED = Gauge(
    "vehicle_speed_kph",
    "Current vehicle speed in kilometres per hour",
    ["vehicle_id"]
)


VEHICLE_BATTERY = Gauge(
    "vehicle_battery_percent",
    "Current vehicle battery percentage",
    ["vehicle_id"]
)


VEHICLE_TEMPERATURE = Gauge(
    "vehicle_temperature_celsius",
    "Current vehicle temperature",
    ["vehicle_id"]
)


VEHICLE_HEALTH = Gauge(
    "vehicle_health_status",
    "Vehicle health status where 1 means healthy and 0 means unhealthy",
    ["vehicle_id"]
)


# ------------------------------------------------
# Home endpoint
# ------------------------------------------------

@app.route("/")
def home():

    REQUEST_COUNT.labels(
        endpoint="/"
    ).inc()

    app.logger.info(
        "Vehicle Dashboard home endpoint accessed"
    )

    return jsonify({
        "message": "Vehicle Dashboard is running"
    })


# ------------------------------------------------
# Vehicle API
# ------------------------------------------------

@app.route("/api/vehicle")
def get_vehicle_data():

    start_time = time.time()

    vehicle_id = "VEHICLE-001"

    speed = random.randint(0, 120)

    battery = random.randint(20, 100)

    temperature = random.randint(25, 90)


    # Check vehicle health

    if battery < 30:

        status = "Warning"

        health_value = 0

        app.logger.error(
            "Low battery detected: "
            "vehicle_id=%s battery=%s",
            vehicle_id,
            battery
        )


    elif temperature > 80:

        status = "Warning"

        health_value = 0

        app.logger.error(
            "High temperature detected: "
            "vehicle_id=%s temperature=%s",
            vehicle_id,
            temperature
        )


    else:

        status = "Healthy"

        health_value = 1

        app.logger.info(
            "Vehicle is healthy: "
            "vehicle_id=%s speed=%s "
            "battery=%s temperature=%s",
            vehicle_id,
            speed,
            battery,
            temperature
        )


    # ------------------------------------------------
    # Existing Prometheus metrics
    # ------------------------------------------------

    REQUEST_COUNT.labels(
        endpoint="/api/vehicle"
    ).inc()


    VEHICLE_SPEED.labels(
        vehicle_id=vehicle_id
    ).set(speed)


    VEHICLE_BATTERY.labels(
        vehicle_id=vehicle_id
    ).set(battery)


    VEHICLE_TEMPERATURE.labels(
        vehicle_id=vehicle_id
    ).set(temperature)


    VEHICLE_HEALTH.labels(
        vehicle_id=vehicle_id
    ).set(health_value)


    # Request duration

    duration = time.time() - start_time


    REQUEST_DURATION.labels(
        endpoint="/api/vehicle"
    ).observe(duration)


    app.logger.info(
        "Request completed: "
        "endpoint=/api/vehicle "
        "vehicle_id=%s status=%s "
        "duration_seconds=%.4f",
        vehicle_id,
        status,
        duration
    )


    return jsonify({

        "vehicle_id": vehicle_id,

        "speed": speed,

        "battery": battery,

        "temperature": temperature,

        "ota_version": "v1.0.0",

        "status": status

    })


# ------------------------------------------------
# Prometheus /metrics
# ------------------------------------------------

app.wsgi_app = DispatcherMiddleware(
    app.wsgi_app,
    {
        "/metrics": make_wsgi_app()
    }
)


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000
    )