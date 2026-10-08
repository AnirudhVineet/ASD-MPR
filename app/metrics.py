"""Prometheus metrics: HTTP traffic, auth activity and business gauges."""

import time

from flask import Blueprint, Response, g, request
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Histogram, generate_latest

bp = Blueprint("metrics", __name__)

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
LOGINS = Counter("clubapp_logins_total", "Login attempts", ["result"])
REGISTRATIONS = Counter("clubapp_registrations_total", "New user registrations")
RSVPS = Counter("clubapp_rsvps_total", "RSVP actions", ["action"])
MEMBERSHIP_CHANGES = Counter("clubapp_membership_changes_total", "Club joins/leaves", ["action"])


def _endpoint_label() -> str:
    # Use the URL rule (e.g. /clubs/<int:club_id>) rather than the raw path to bound cardinality
    return request.url_rule.rule if request.url_rule is not None else "unmatched"


def init_app(app) -> None:
    @app.before_request
    def _start_timer():
        g._metrics_start = time.perf_counter()

    @app.after_request
    def _record(response):
        start = g.pop("_metrics_start", None)
        if start is not None:
            endpoint = _endpoint_label()
            REQUEST_LATENCY.labels(request.method, endpoint).observe(time.perf_counter() - start)
            REQUEST_COUNT.labels(request.method, endpoint, str(response.status_code)).inc()
        return response

    app.register_blueprint(bp)


@bp.route("/metrics")
def metrics_endpoint():
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)
