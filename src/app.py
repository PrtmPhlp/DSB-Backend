#!/usr/bin/env python3
# ------------------------------------------------
"""
Backend for scraped and formatted data

__author__ = "PrtmPhlp"
__Contact__ = "contact@pertermann.de"
__Status__ = "Development"
"""
# ------------------------------------------------
# ! Imports

import json
import socket
from flask import Flask, Response, abort, jsonify, request
from flask_cors import CORS # pylint: disable=E0401 # type: ignore
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
import os

from logger import setup_logger

# Initialize logger
logger = setup_logger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Setup the Flask-JWT-Extended extension
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-keysädaöfkjsäöadlfk')  # Change this!
jwt = JWTManager(app)

# Mock user database (replace with a real database in production)
users = {
    "274583": generate_password_hash("johann")
}

def load_json_file():
    """
    Load JSON data from file.

    Returns:
        dict: Loaded JSON data or empty dict with 'substitution' key if error occurs.
    """
    try:
        with open('json/formatted.json', 'r', encoding='utf-8') as schema_file:
            return json.load(schema_file)
    except FileNotFoundError:
        logger.info("Error: The file 'json/formatted.json' was not found.")
    except json.JSONDecodeError:
        logger.info("Error: Failed to decode JSON from the file.")
    return {"substitution": []}

@app.route('/', methods=['GET'])
def hello_world() -> Response:
    """
    Man Page for the Unofficial DSBmobile API Server.

    Returns:
        Response: HTML formatted man page with API details.
    """
    man_page = """
    <h1>Unofficial DSBmobile API Server</h1>
    <h2>Available Endpoints</h2>
    <pre>
    1. /                     - Display this man page.
    2. /api/                 - Retrieve all substitution plans.
    3. /api/&lt;task_id&gt;/       - Retrieve a specific substitution entry by index.
    4. /api/&lt;task_id&gt;/&lt;content_id&gt;/ - Retrieve a specific content item from a substitution entry.
    5. /api/healthcheck      - Check the health status of the API server.
    </pre>
    <h2>Endpoint Descriptions</h2>
    <pre>
    /api/                   : Returns a JSON object containing all substitution plans.
                              Example: GET /api/

    /api/&lt;task_id&gt;/          : Returns a specific substitution entry identified by its index.
                              Example: GET /api/1/

    /api/&lt;task_id&gt;/&lt;content_id&gt;/ : Returns a specific content item from a substitution entry.
                              Example: GET /api/1/2/

    /api/healthcheck      : Simple endpoint to check the health of the server.
                              Example: GET /api/healthcheck
    </pre>
    <h2>Contact</h2>
    <p>Author: <a href="https://pertermann.de">PrtmPhlp</a></p>
    <p>Contact: <a href="mailto:contact@pertermann.de">contact@pertermann.de</a></p>
    <p>Status: Development</p>
    """
    return Response(man_page, mimetype='text/html')

@app.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token.

    Returns:
        dict: JWT access token or error message.
    """
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400

    if username not in users or not check_password_hash(users[username], password):
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200

@app.route('/api/', methods=['GET'])
@jwt_required()
def get_plans() -> Response:
    """
    Retrieve all plans.

    Returns:
        Response: A JSON response containing all plans.
    """
    plans = load_json_file()
    return jsonify(plans)

@app.route('/api/<int:task_id>/', methods=['GET'])
@jwt_required()
def get_plan(task_id: int) -> Response:
    """
    Retrieve a single substitution entry by its index.

    Args:
        task_id (int): The index of the substitution entry.

    Returns:
        Response: A JSON response containing the substitution entry, or a 404 error if not found.
    """
    plans = load_json_file()
    try:
        substitution = plans['substitution'][task_id]
        return jsonify(substitution)
    except IndexError:
        abort(404, description="Substitution entry not found")

@app.route('/api/<int:task_id>/<int:content_id>/', methods=['GET'])
@jwt_required()
def get_content(task_id: int, content_id: int) -> Response:
    """
    Retrieve a specific content item from a substitution entry.

    Args:
        task_id (int): The index of the substitution entry.
        content_id (int): The index of the content item within the substitution entry.

    Returns:
        Response: A JSON response containing the content item, or a 404 error if not found.
    """
    plans = load_json_file()
    try:
        substitution = plans['substitution'][task_id]
        content = substitution['content'][content_id]
        return jsonify(content)
    except IndexError:
        abort(404, description="Content item not found")

@app.route("/api/healthcheck", methods=["GET"])
def healthcheck():
    """
    Check the health of the server.

    Returns:
        dict: Health status message.
    """
    return {"status": "success", "message": "Flask API for DSBMobile data"}

if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    app.run(host='0.0.0.0', port=5555, debug=True)
    print(f"Server running on http://{local_ip}:5555")
