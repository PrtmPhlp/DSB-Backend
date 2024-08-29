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
from flask import Flask, jsonify, abort, Response
import logging
import coloredlogs

# ------------------------------------------------
# S: Logger
logger = logging.getLogger(__name__)
LOGGING_LEVEL = logging.INFO
logging.basicConfig(level=LOGGING_LEVEL)
coloredlogs.install(
    fmt="%(asctime)s - %(levelname)s - \033[94m%(message)s\033[0m",
    datefmt="%H:%M:%S",
    level=LOGGING_LEVEL,
)
# ------------------------------------------------

app = Flask(__name__)

# Load JSON from file json/schema-sample.json
try:
    with open('json/formatted.json', 'r', encoding='utf-8') as schema_file:
        plans = json.load(schema_file)
except FileNotFoundError:
    logger.info("Error: The file 'json/formatted.json' was not found.")
    plans = {"substitution": []}
except json.JSONDecodeError:
    logger.info("Error: Failed to decode JSON from the file.")
    plans = {"substitution": []}


@app.route('/plan/', methods=['GET'])
def get_plans() -> Response:
    """
    Retrieve all plans.

    Returns:
        Response: A JSON response containing all plans.
    """
    return jsonify(plans)


@app.route('/plan/<int:task_id>', methods=['GET'])
def get_plan(task_id: int) -> Response:
    """
    Retrieve a single substitution entry by its index.

    Args:
        task_id (int): The index of the substitution entry.

    Returns:
        Response: A JSON response containing the substitution entry, or a 404 error if not found.
    """
    try:
        substitution = plans['substitution'][task_id]
        return jsonify(substitution)
    except IndexError:
        abort(404, description="Substitution entry not found")


@app.route('/plan/<int:task_id>/<int:content_id>', methods=['GET'])
def get_content(task_id: int, content_id: int) -> Response:
    """
    Retrieve a specific content item from a substitution entry.

    Args:
        task_id (int): The index of the substitution entry.
        content_id (int): The index of the content item within the substitution entry.

    Returns:
        Response: A JSON response containing the content item, or a 404 error if not found.
    """
    try:
        substitution = plans['substitution'][task_id]
        content = substitution['content'][content_id]
        return jsonify(content)
    except IndexError:
        abort(404, description="Content item not found")


if __name__ == '__main__':
    app.run(debug=True)
