from flask import Flask, request, jsonify, g
import os
import socket
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

app = Flask(__name__)

INSTANCE_NAME = os.getenv("INSTANCE_NAME", socket.gethostname())
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- Logger config (stdout for Docker) ---
logger = logging.getLogger("app")
logger.setLevel(LOG_LEVEL)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)s instance=%(instance)s request_id=%(request_id)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
handler.setFormatter(formatter)

# Prevent adding handler multiple times
if not logger.handlers:
    logger.addHandler(handler)
logger.propagate = False


def _get_request_id():
    # If nginx sends it, use that
    rid = request.headers.get("X-Request-ID")
    return rid or str(uuid.uuid4())


@app.before_request
def before_request():
    g.start_time = time.time()
    g.request_id = _get_request_id()


@app.after_request
def after_request(response):
    duration_ms = int((time.time() - g.start_time) * 1000)

    # Return request id header so client side can also trace it
    response.headers["X-Request-ID"] = g.request_id

    client_ip = request.headers.get("X-Real-IP", request.remote_addr)
    method = request.method
    path = request.path
    status = response.status_code
    ua = request.headers.get("User-Agent", "-")

    logger.info(
        f'{method} {path} status={status} duration_ms={duration_ms} client_ip={client_ip} ua="{ua}"',
        extra={"instance": INSTANCE_NAME, "request_id": g.request_id},
    )
    return response


@app.get("/")
def index():
    return jsonify({
        "message": "Hello from Flask behind Nginx Load Balancer!",
        "instance": INSTANCE_NAME,
        "hostname": socket.gethostname(),
        "request_id": g.request_id,
        "client_ip": request.headers.get("X-Real-IP", request.remote_addr),
        "time_utc": datetime.now(timezone.utc).isoformat()
    })


@app.get("/healthz")
def healthz():
    return "ok", 200
