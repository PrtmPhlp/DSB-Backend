#!/usr/bin/env python3
# ------------------------------------------------
"""
This script formats the scraped data from 'json/scraped.json' and saves it to 'json/formatted.json'.

__author__ = "PrtmPhlp"
__Contact__ = "contact@pertermann.de"
__Status__ = "Development"
"""
# ------------------------------------------------
# ! Imports
import argparse
import json
from datetime import datetime
from typing import Any, Dict, List

from logger import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Constants
WEEKDAY_MAP: Dict[str, int] = {
    "Montag": 1,
    "Dienstag": 2,
    "Mittwoch": 3,
    "Donnerstag": 4,
    "Freitag": 5,
    "Samstag": 6,
    "Sonntag": 7
}


def create_substitution_entry(day: str, date: str, entries: List[List[str]]) -> Dict[str, Any]:
    """
    Creates a substitution entry for a specific day.

    Args:
        day (str): The name of the weekday (e.g., 'Donnerstag').
        entries (List[List[str]]): List of entries where each entry is a list of strings.

    Returns:
        Dict[str, Any]: A dictionary representing the substitution entry.
    """
    if not hasattr(create_substitution_entry, "call_count"):
        create_substitution_entry.call_count = 0

    # Increment the counter each time the function is called
    create_substitution_entry.call_count += 1

    iso_weekday_number = WEEKDAY_MAP.get(day, 0)

    substitution_entry = {
        "id": str(create_substitution_entry.call_count),
        "date": date,
        "weekDay": [str(iso_weekday_number), day],
        "content": []
    }
    last_position = None

    for entry in entries:
        position = entry[1] if entry[1] else last_position
        content_entry = {
            "position": position,
            "teacher": entry[2],
            "subject": entry[3],
            "room": entry[4],
            "topic": entry[5],
            "info": entry[6]
        }
        if position:
            last_position = position
        substitution_entry["content"].append(content_entry)

    return substitution_entry


def fill_json_template(changes_detected: bool, json_data: Dict[str, List[List[str]]], course: str) -> Dict[str, Any]:
    """
    Fills in the JSON template with the provided data.

    Args:
        json_data (Dict[str, List[List[str]]]): The JSON data to process.
        course (str): The course name.

    Returns:
        Dict[str, Any]: The filled JSON template.
    """
    output_json = {
        "createdAt": datetime.now().isoformat(),
        "class": course,
        "substitution": []
    }
    if not changes_detected:
        # logger.error("No changes detected in the scraped data.")
        return output_json  # Return early if no changes detected

    for day, entries in json_data.items():
        # Splitting the string using '_'
        day, date = day.split('_')
        try:
            substitution_entry = create_substitution_entry(day, date, entries)
            output_json["substitution"].append(substitution_entry)
        except Exception as e:  # pylint: disable=W0718
            logger.error("Error processing day '%s': %s", day, e)
    return output_json


def main(changes_detected: bool, course: str, input_file: str, output_file: str) -> None:
    """
    Main function to process the JSON data and save the output.

    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to the output JSON file.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            json_data: Dict[str, List[List[str]]] = json.load(file)
    except FileNotFoundError:
        logger.error("The file '%s' was not found.", input_file)
        return
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from the file '%s'.", input_file)
        return

    filled_json = fill_json_template(changes_detected, json_data, course)

    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(filled_json, file, indent=4, ensure_ascii=False)
    except Exception as e:  # pylint: disable=W0718
        logger.error("Error saving data to '%s': %s", output_file, e)
        return

    if changes_detected:
        logger.info("JSON template filled and saved to '%s'", output_file)


# Example usage
if __name__ == "__main__":
    # DEFAULT VALUES
    INPUT_FILE = "json/scraped.json"
    default_args = argparse.Namespace(
        course='MSS12', output_dir='json/formatted.json')
    main(default_args.course, INPUT_FILE, default_args.output_dir)
    # from os import system # type: ignore
    # system("cat json/formatted.json | jq") # type: ignore
