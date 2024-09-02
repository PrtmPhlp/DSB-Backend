#!/usr/bin/env python3
# ------------------------------------------------
"""
This script validates 'json/formatted.json' against the schema in 'json/schema.json'.

__author__ = "PrtmPhlp"
__Contact__ = "contact@pertermann.de"
__Status__ = "Development"
"""
# ------------------------------------------------
# ! Imports

import json

import jsonschema
import jsonschema.exceptions

from logger import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# ------------------------------------------------

# Load the schema


def main(schema_file, json_file):
    """
    Validates a JSON file against a provided JSON schema.

    Args:
        schema_file (str): The path to the JSON schema file.
        json_file (str): The path to the JSON file to be validated.
    """
    with open(schema_file, 'r', encoding='utf-8') as schema_file_content:
        schema = json.load(schema_file_content)

    # Load the JSON file to be validated
    with open(json_file, 'r', encoding='utf-8') as json_file_content:
        json_data = json.load(json_file_content)

    # Validate the JSON file against the schema
    try:
        jsonschema.validate(instance=json_data, schema=schema)
        logger.info("JSON file is valid.")
    except jsonschema.exceptions.ValidationError:
        logger.error("JSON file is invalid.")
        raise


if __name__ == "__main__":
    main('json/schema.json', 'json/formatted.json')
