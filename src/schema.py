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

# ------------------------------------------------

# Load the schema

with open('json/schema.json', 'r', encoding='utf-8') as schema_file:
    schema = json.load(schema_file)

# Load the JSON file to be validated
with open('json/formatted.json', 'r', encoding='utf-8') as json_file:
    json_data = json.load(json_file)

# Validate the JSON file against the schema
try:
    jsonschema.validate(instance=json_data, schema=schema)
    print("JSON file is valid.")
except jsonschema.exceptions.ValidationError as e:  # type: ignore
    print("JSON file is invalid.")
    print("Error:", e.message)
