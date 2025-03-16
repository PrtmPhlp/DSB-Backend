#!/usr/bin/env python3
# -----------------------------------------------------------
"""
Flask-based backend with:
- 10 requests/second rate limit (Flask-Limiter)
- JWT-based authentication (flask_jwt_extended)
- Colored logging (logger_setup.py)
- Minimal routes, no OpenAPI docs

Installation:
  pip install flask flask_cors flask_jwt_extended flask_limiter waitress \
              werkzeug coloredlogs
"""

import os
import json
import socket
import logging
from typing import Any, Dict

from flask import Flask, Blueprint, Response, abort, jsonify, make_response, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash
from waitress import serve

# Rate-limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Logging from external file
from logger_setup import LoggerSetup

# -----------------------------------------------------------
# 1) Logger Setup
# -----------------------------------------------------------
logger = LoggerSetup.setup_logger(__name__, logging.INFO)

# -----------------------------------------------------------
# 2) Blueprint & Auth Setup
# -----------------------------------------------------------
api_bp = Blueprint("api", __name__)

# Mock user database
users_db = {
    "274583": generate_password_hash("johann")
}

def load_json_file(path: str = "json/teacher_replaced.json") -> Dict[str, Any]:
    """
    Load JSON data from the specified file. Return fallback if unavailable.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("File '%s' not found.", path)
    except json.JSONDecodeError:
        logger.warning("JSON decode error for file '%s'.", path)
    return {"substitution": []}


# -----------------------------------------------------------
# 3) Routes
# -----------------------------------------------------------
@api_bp.after_request
def cors_after_request(response):
    """
    Apply a simple CORS policy after every request, including OPTIONS handling.
    """
    if request.method == 'OPTIONS':
        resp = make_response()
        resp.headers.add('Access-Control-Allow-Origin',
                         request.headers.get('Origin', '*'))
        resp.headers.add('Access-Control-Allow-Headers',
                         'Content-Type, Authorization')
        resp.headers.add('Access-Control-Allow-Methods',
                         'GET, POST, PUT, DELETE, OPTIONS')
        resp.headers.add('Access-Control-Allow-Credentials', 'true')
        resp.headers.add('Access-Control-Max-Age', '3600')
        resp.status_code = 204
        return resp

    origin = request.headers.get('Origin')
    if origin:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response


@api_bp.route('/', methods=['GET'])
def man_page() -> Response:
    """
    Man page with minimal info on available endpoints. No doc generation.
    """
    html = """
    <h1>Unofficial DSBmobile API Server</h1>
    <p>This API is <strong>rate-limited to 10 requests per second</strong>.</p>
    <h2>Available Endpoints</h2>
    <pre>
    GET /                 - This man page
    POST /login           - Authenticate & receive JWT
    GET /api/             - Retrieve all plans (JWT required)
    GET /healthcheck  - Check server health
    </pre>
    """
    return Response(html, mimetype='text/html')


@api_bp.route("/login", methods=["OPTIONS", "POST"])
def login():
    """
    Authenticate user with a username & password, returning a JWT if valid.
    """
    if request.method == "OPTIONS":
        return make_response(), 204

    # Accept either JSON or form data
    if not (request.is_json or request.form):
        return jsonify({"msg": "Missing JSON or form data."}), 400

    username = request.form.get('username') if request.form else request.json.get('username')
    password = request.form.get('password') if request.form else request.json.get('password')

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400

    # Validate credentials
    user_hash = users_db.get(username)
    if not user_hash or not check_password_hash(user_hash, password):
        abort(401, description="Bad username or password")

    token = create_access_token(identity=username)
    return jsonify(access_token=token), 200


@api_bp.route("/api/", methods=["GET"])
@jwt_required()
def get_all_plans():
    """
    Return all substitution data from json/teacher_replaced.json, if any (requires JWT).
    """
    data = load_json_file("json/teacher_replaced.json")
    return jsonify(data), 200


# @api_bp.route("/api/<int:task_id>/", methods=["GET"])
# @jwt_required()
# def get_single_plan(task_id: int):
#     """
#     Return a single plan by index (requires JWT).
#     """
#     data = load_json_file("json/teacher_replaced.json")
#     try:
#         plan = data["substitution"][task_id]
#         return jsonify(plan), 200
#     except IndexError:
#         abort(404, description="Plan not found")


# @api_bp.route("/api/<int:task_id>/<int:content_id>/", methods=["GET"])
# @jwt_required()
# def get_plan_content(task_id: int, content_id: int):
#     """
#     Return a specific content item from a plan (requires JWT).
#     """
#     data = load_json_file("json/teacher_replaced.json")
#     try:
#         plan = data["substitution"][task_id]
#         content = plan["content"][content_id]
#         return jsonify(content), 200
#     except IndexError:
#         abort(404, description="Content item not found")


@api_bp.route("/healthcheck", methods=["GET"])
def healthcheck():
    """
    Check the health of the server (no auth required).
    """
    return jsonify({"status": "success", "message": "Flask API for DSBMobile data"}), 200


# -----------------------------------------------------------
# 4) Application Factory
# -----------------------------------------------------------
def create_app() -> Flask:
    """
    Creates and configures the Flask application with:
      - JWT
      - Rate limiting (10 requests/second)
    """
    from flask_limiter import Limiter
    from flask_jwt_extended import JWTManager
    from flask_cors import CORS

    app = Flask(__name__)
    # Minimal secret key for JWT (change for production)
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "your-secret-key")

    # Rate-limit: default 10 req/sec for all endpoints
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["10 per second"]
    )

    # JWT
    jwt = JWTManager(app)

    # Register blueprint
    app.register_blueprint(api_bp)

    # CORS
    CORS(app)

    return app

# -----------------------------------------------------------
# 5) Main
# -----------------------------------------------------------
if __name__ == "__main__":
    DEVELOPMENT = True
    flask_app = create_app()

    if DEVELOPMENT:
        logger.info("Running in development mode: http://0.0.0.0:5555")
        flask_app.run(host="0.0.0.0", port=5555, debug=True)
    else:
        local_ip = socket.gethostbyname(socket.gethostname())
        logger.info("Production mode at http://%s:5555", local_ip)
        serve(flask_app, host="0.0.0.0", port=5555, _quiet=False)
