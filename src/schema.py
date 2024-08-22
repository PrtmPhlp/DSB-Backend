import json
import jsonschema
from jsonschema import validate

# Load the schema

with open('json/schema.json', 'r', encoding='utf-8') as schema_file:
    schema = json.load(schema_file)

# Load the JSON file to be validated
with open('json/schema-sample.json', 'r', encoding='utf-8') as json_file:
    json_data = json.load(json_file)

# Validate the JSON file against the schema
try:
    validate(instance=json_data, schema=schema)
    print("JSON file is valid.")
except jsonschema.exceptions.ValidationError as e:  # type: ignore
    print("JSON file is invalid.")
    print("Error:", e.message)
