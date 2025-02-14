#!/usr/bin/env python3
# -----------------------------------------------------------
"""
A single-file solution that:
1) Loads credentials for dsbmobile.com (from .env or OS).
2) Scrapes the "DaVinci Touch" section for class/course replacements.
3) Saves raw data to a JSON file only if changes are detected.
4) Formats that JSON data into a final structure.
5) Replaces teacher codes with full names from lehrer.json
6) Optionally validates the final JSON with a JSON schema.

Run: 
  python unified_scraper.py [options]

Dependencies:
  - requests
  - beautifulsoup4
  - python-dotenv
  - coloredlogs
  - PyDSB
  - jsonschema
  - ./logger_setup.py
"""

import argparse
import logging
import os
import sys
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup
import jsonschema
from dotenv import dotenv_values
from PyDSB import PyDSB

# Logging from external file
from logger_setup import LoggerSetup

# -----------------------------------------------------------
# 1) Logger Setup
# -----------------------------------------------------------
logger = LoggerSetup.setup_logger(__name__, logging.INFO)

# -----------------------------------------------------------
# 2) Environment + Credential Handling
# -----------------------------------------------------------
class EnvCredentialsLoader:
    """
    Loads dsbmobile.com credentials from a .env file or OS environment variables.
    """

    def __init__(self, env_file: str = ".env"):
        """
        Initialize the loader with a path to the .env file.

        Args:
            env_file (str): Path to the .env file. Default ".env".
        """
        self.env_file = env_file
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__)

    def load_env_credentials(self) -> dict:
        """
        Load environment credentials from .env or OS environment variables.

        Returns:
            dict: Dictionary containing 'DSB_USERNAME' and 'DSB_PASSWORD'.

        Raises:
            ValueError: If credentials are missing or not found.
        """
        def mask_string(s: str) -> str:
            """Masks all but the first three characters of a string."""
            if len(s) <= 3:
                return s
            return s[:3] + "*" * (len(s) - 3)

        # Attempt loading from .env
        credentials = {}
        try:
            env_values = dotenv_values(self.env_file)
            if env_values and "DSB_USERNAME" in env_values and "DSB_PASSWORD" in env_values:
                credentials = {
                    "DSB_USERNAME": env_values["DSB_USERNAME"],
                    "DSB_PASSWORD": env_values["DSB_PASSWORD"]
                }
                # Ensure none are None
                if not credentials["DSB_USERNAME"] or not credentials["DSB_PASSWORD"]:
                    raise ValueError
                self.logger.info("Loaded credentials from .env file.")
            else:
                raise ValueError
        except (FileNotFoundError, ValueError):
            self.logger.warning(
                "Failed to load credentials from .env, attempting OS environment..."
            )
            # Fallback to OS environment
            dsb_username = os.getenv("DSB_USERNAME")
            dsb_password = os.getenv("DSB_PASSWORD")
            if not dsb_username or not dsb_password:
                raise ValueError("DSB_USERNAME and DSB_PASSWORD must be set.")
            credentials = {
                "DSB_USERNAME": dsb_username,
                "DSB_PASSWORD": dsb_password
            }

        # Log masked credentials
        self.logger.info(
            "Using Username: %s, Password: %s",
            mask_string(credentials["DSB_USERNAME"]),
            mask_string(credentials["DSB_PASSWORD"])
        )
        return credentials


# -----------------------------------------------------------
# 3) Scraper (Fetching and Parsing)
# -----------------------------------------------------------
class DSBScraper:
    """
    Encapsulates all logic to:
      - Fetch data from dsbmobile.com
      - Parse relevant HTML structures
      - Compare changes and save to JSON
    """

    def __init__(self, username: str, password: str):
        """
        Initializes the DSBScraper with given credentials.

        Args:
            username (str): The dsbmobile.com username.
            password (str): The dsbmobile.com password.
        """
        self.username = username
        self.password = password
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__)

    def prepare_api_url(self) -> str:
        """
        Prepare the API URL for the "DaVinci Touch" section.

        Returns:
            str: The URL for the "DaVinci Touch" section.

        Raises:
            ValueError: If the "DaVinci Touch" section is not found.
            requests.ConnectionError: If there's no internet or request fails.
        """
        self.logger.info("Attempting to fetch postings via PyDSB.")
        try:
            dsb = PyDSB(self.username, self.password)
            data = dsb.get_postings()  # returns a list of postings
        except requests.ConnectionError as e:
            self.logger.critical("No Internet Connection: %s", e)
            raise

        for section in data:
            if section["title"] == "DaVinci Touch":
                base_url = section["url"]
                self.logger.debug("DaVinci Touch URL found: %s", base_url)
                return base_url

        raise ValueError("DaVinci Touch section not found in dsbmobile postings.")

    def _request_url_data(self, url: str) -> BeautifulSoup:
        """
        Internal helper: GET the specified URL, parse via BeautifulSoup.

        Args:
            url (str): The URL to fetch.

        Returns:
            BeautifulSoup: Parsed HTML document.

        Raises:
            requests.exceptions.RequestException: For any network or HTTP errors.
        """
        self.logger.debug("Requesting data from URL: %s", url)
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to fetch data from %s: %s", url, e)
            raise

    def get_plans(self, base_url: str) -> Dict[str, str]:
        """
        Parse the base URL to get all day-indexed plan links.

        Args:
            base_url (str): The main "DaVinci Touch" URL.

        Returns:
            Dict[str, str]: Mapping "Day_Date" -> "URL".
        """
        soup = self._request_url_data(base_url)
        posts_dict = {}

        try:
            day_index = soup.find("ul", class_="day-index")
            if not day_index:
                self.logger.warning("No 'ul.day-index' found. Possibly no plans available.")
                return posts_dict
            links = day_index.find_all("a")

            if not links:
                self.logger.warning("No <a> tags found within '.day-index'.")
                return posts_dict

            href_links = [link.get("href") for link in links]
            text_list = [link.get_text(strip=True) for link in links]

            # e.g. "02.09.2024 Mittwoch" -> "Mittwoch_02-09-2024"
            for href, text in zip(href_links, text_list):
                parts = text.split()
                if len(parts) == 2:
                    date_str, weekday_str = parts[0], parts[1]
                    new_key = f"{weekday_str}_{date_str.replace('.', '-')}"
                    full_url = requests.compat.urljoin(base_url, href)
                    posts_dict[new_key] = full_url
                    self.logger.debug("Found plan: %s -> %s", new_key, full_url)
                else:
                    self.logger.warning(
                        "Unexpected link text format: '%s'. Skipped.", text
                    )
        except AttributeError as e:
            self.logger.error("Error parsing HTML structure for day-index: %s", e)
            raise

        return posts_dict

    def _scrape_single_plan(
        self, plan_url: str, course: str
    ) -> Tuple[List[List[str]], bool]:
        """
        Scrapes a single plan URL for table rows matching the given course.

        Returns:
            (List[List[str]], bool): A tuple of:
              - A list of table rows (each row is a list of strings) for matched course
              - A boolean indicating if the course was found.
        """
        soup = self._request_url_data(plan_url)
        success = False
        total_replacements: List[List[str]] = []

        try:
            table = soup.find("table")
            if not table:
                raise ValueError("Table element not found in HTML.")

            rows = table.find_all("tr")
            for row in rows:
                columns = row.find_all("td")
                if not columns:
                    continue

                # Compare first cell with 'course'
                if columns[0].get_text(strip=True) == course:
                    success = True
                    self.logger.debug("Course '%s' found in row: %s", course, row)
                    replacement = [col.get_text(strip=True) for col in columns]
                    total_replacements.append(replacement)

                    # Also gather subsequent rows that belong to this entry 
                    next_row = row.find_next_sibling("tr")
                    while next_row and "\xa0" in next_row.find("td").get_text():
                        columns_next = next_row.find_all("td")
                        rep_next = [col.get_text(strip=True) for col in columns_next]
                        total_replacements.append(rep_next)
                        next_row = next_row.find_next_sibling("tr")

        except Exception as e:
            self.logger.error("Error scraping %s: %s", plan_url, e)
            raise

        return total_replacements, success

    def scrape_all_plans(
        self, posts_dict: Dict[str, str], course: str, print_output: bool = False
    ) -> Dict[str, List[List[str]]]:
        """
        For each day-index plan URL, scrape its table for rows about `course`.
        """
        result = {}
        for day_key, url in posts_dict.items():
            rows, success = self._scrape_single_plan(url, course)
            result[day_key] = rows
            if success:
                self.logger.info("Matched course '%s' in plan: %s", course, day_key)
            else:
                self.logger.warning("Course '%s' not found in plan: %s", course, day_key)

        if print_output:
            pretty_json = json.dumps(result, indent=2, ensure_ascii=False)
            self.logger.info("Scrape Result:\n%s", pretty_json)
        return result

    def save_data_if_changed(self, new_data: dict, file_path: str) -> bool:
        """
        Compare `new_data` to existing file contents and save only if changed.
        """
        existing_data = None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        if existing_data == new_data:
            self.logger.info("No changes detected. Skipping save.")
            return False

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
        self.logger.info("Scraped data saved to %s", file_path)
        return True


# -----------------------------------------------------------
# 4) JSON Formatting
# -----------------------------------------------------------
class JSONFormatter:
    """
    Converts the raw scraped data into a final structured JSON format.
    """

    def __init__(self):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__)
        self.WEEKDAY_MAP = {
            "Montag": 1,
            "Dienstag": 2,
            "Mittwoch": 3,
            "Donnerstag": 4,
            "Freitag": 5,
            "Samstag": 6,
            "Sonntag": 7
        }
        self.entry_counter = 0

    def _create_substitution_entry(
        self, weekday: str, date: str, entries: List[List[str]]
    ) -> Dict[str, Any]:
        """
        Builds a single day's substitution object.
        """
        self.entry_counter += 1

        iso_weekday_num = self.WEEKDAY_MAP.get(weekday, 0)
        substitution_entry = {
            "id": str(self.entry_counter),
            "date": date,
            "weekDay": [str(iso_weekday_num), weekday],
            "content": []
        }

        last_position = None
        for entry in entries:
            # [0:course, 1:position, 2:teacher, 3:subject, 4:room, 5:topic, 6:info]
            position = entry[1] if len(entry) > 1 else None
            if position == "":
                position = last_position

            content_piece = {
                "position": position if position else "",
                "teacher": entry[2] if len(entry) > 2 else "",
                "subject": entry[3] if len(entry) > 3 else "",
                "room":    entry[4] if len(entry) > 4 else "",
                "topic":   entry[5] if len(entry) > 5 else "",
                "info":    entry[6] if len(entry) > 6 else ""
            }
            if position:
                last_position = position
            substitution_entry["content"].append(content_piece)

        return substitution_entry

    def format_data(
        self, scraped_data: Dict[str, List[List[str]]], course: str, changes_detected: bool
    ) -> Dict[str, Any]:
        """
        Produce the final JSON structure from the scraped data.
        """
        output = {
            "createdAt": datetime.now().isoformat(),
            "class": course,
            "substitution": []
        }

        if not changes_detected:
            self.logger.info("No changes detected; returning minimal JSON structure.")
            return output

        for key, entries in scraped_data.items():
            if "_" not in key:
                self.logger.warning("Unexpected key format (missing '_'): %s", key)
                continue

            weekday_str, date_str = key.split("_", 1)
            try:
                entry_for_day = self._create_substitution_entry(weekday_str, date_str, entries)
                output["substitution"].append(entry_for_day)
            except Exception as e:
                self.logger.error("Error building substitution entry for '%s': %s", key, e)

        return output


# -----------------------------------------------------------
# 5) JSON Schema Validation
# -----------------------------------------------------------
class JSONSchemaValidator:
    """
    Simple wrapper around jsonschema to validate a JSON file against a schema.
    """

    def __init__(self):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__)

    def validate(self, json_data: dict, schema_file: str) -> None:
        """
        Validate the `json_data` against the JSON schema from `schema_file`.
        """
        try:
            with open(schema_file, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            jsonschema.validate(instance=json_data, schema=schema)
            self.logger.info("JSON data is valid according to '%s'.", schema_file)
        except jsonschema.exceptions.ValidationError as e:
            self.logger.error("JSON data is invalid: %s", e.message)
            raise


# -----------------------------------------------------------
# 6) TEACHER REPLACER Integration
# -----------------------------------------------------------
def replace_teacher_codes(data: Dict[str, Any], teacher_mapping: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """
    Replace teacher codes (like 'Ar', '(Bo)') with actual names from teacher_mapping.

    teacher_mapping expected to be dict:
      {
        "Ar": {
           "Name": "Peter Muster",
           "Nachname": "Muster",
           "Vorname": "Peter",
           "Fächer": "M, Mu"
        },
        ...
      }
    """
    for substitution in data.get("substitution", []):
        for item in substitution.get("content", []):
            if "teacher" in item:
                code = item["teacher"]
                clean_code = code.strip('()')  # remove parentheses
                if clean_code in teacher_mapping:
                    old_value = item["teacher"]
                    name = teacher_mapping[clean_code]['Nachname']
                    # If original code was in parentheses, keep parentheses around the name
                    item["teacher"] = f"({name})" if code.startswith('(') else name
                    logger.info("CHANGE: teacher: changed '%s' to '%s'", old_value, item["teacher"])
    return data


# -----------------------------------------------------------
# 7) CLI + Main Orchestrator
# -----------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape data from dsbmobile.com, format it, replace teacher codes, and optionally validate."
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging.")
    parser.add_argument("-c", "--course", default="MSS12", help="Which course to scrape. Default: MSS12")
    parser.add_argument("-p", "--print-output", action="store_true",
                        help="Print raw JSON output after scraping.")
    parser.add_argument("-o", "--output-dir", default="json/formatted.json",
                        help="Path for the formatted JSON output. Default: json/formatted.json")
    parser.add_argument("--raw-file", default="json/scraped.json",
                        help="Path for the raw scraped JSON data. Default: json/scraped.json")
    parser.add_argument("--schema-file", default="schema/schema.json",
                        help="Path to the JSON schema file. Default: schema/schema.json")
    parser.add_argument("--teacher-file", default="schema/lehrer.json",
                        help="Path to the teacher mapping file. Default: schema/lehrer.json")
    parser.add_argument("--teacher-replaced-file", default="json/teacher_replaced.json",
                        help="Output file after teacher code replacement. Default: json/teacher_replaced.json")
    parser.add_argument("-d", "--development", action="store_true", default=False,
                        help="If set, do not exit early when no changes are detected.")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Configure logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    LoggerSetup.setup_logger("UnifiedScraper", log_level)

    logger.info("Starting unified DSB scraping process...")

    # Step 1: Load credentials
    creds_loader = EnvCredentialsLoader()
    try:
        creds = creds_loader.load_env_credentials()
    except ValueError as e:
        logger.critical("Could not load credentials: %s", e)
        sys.exit(1)

    # Step 2: Scrape
    scraper = DSBScraper(creds["DSB_USERNAME"], creds["DSB_PASSWORD"])
    try:
        base_url = scraper.prepare_api_url()
    except Exception as e:
        logger.critical("Failed to prepare API URL: %s", e)
        sys.exit(1)

    plans_dict = scraper.get_plans(base_url)
    raw_data = scraper.scrape_all_plans(plans_dict, args.course, args.print_output)

    # Step 3: Compare & Save raw JSON if changed
    changes_detected = scraper.save_data_if_changed(raw_data, args.raw_file)

    # If no changes and not in development mode, skip the rest
    if not changes_detected and not args.development:
        logger.info("No changes detected; exiting early.")
        sys.exit(0)

    # Step 4: Format JSON
    formatter = JSONFormatter()
    final_json = formatter.format_data(raw_data, args.course, changes_detected)

    # Write formatted JSON
    os.makedirs(os.path.dirname(args.output_dir), exist_ok=True)
    try:
        with open(args.output_dir, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)
        logger.info("Formatted data saved to '%s'.", args.output_dir)
    except Exception as e:
        logger.error("Error saving formatted JSON: %s", e)

    # Step 5: Load teacher mapping & replace teacher codes
    try:
        with open(args.teacher_file, "r", encoding="utf-8") as tfile:
            teacher_map = json.load(tfile)
        replaced_data = replace_teacher_codes(final_json, teacher_map)
    except FileNotFoundError:
        logger.warning("Teacher file '%s' not found; skipping teacher code replacement.", args.teacher_file)
        replaced_data = final_json
    except Exception as e:
        logger.error("Error loading teacher file or replacing codes: %s", e)
        replaced_data = final_json

    # Save teacher-replaced output
    os.makedirs(os.path.dirname(args.teacher_replaced_file), exist_ok=True)
    try:
        with open(args.teacher_replaced_file, "w", encoding="utf-8") as f:
            json.dump(replaced_data, f, ensure_ascii=False, indent=4)
        logger.info("Teacher-replaced data saved to '%s'.", args.teacher_replaced_file)
    except Exception as e:
        logger.error("Error saving teacher-replaced JSON: %s", e)

    # Step 6: Validate (optional) using the teacher-replaced JSON
    validator = JSONSchemaValidator()
    try:
        validator.validate(replaced_data, args.schema_file)
    except jsonschema.exceptions.ValidationError:
        logger.critical("Validation failed on teacher-replaced data. Exiting with error status.")
        sys.exit(1)

    logger.info("All steps complete. Exiting.")


if __name__ == "__main__":
    main()
