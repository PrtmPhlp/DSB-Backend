#!/usr/bin/env python3
# -----------------------------------------------------------
"""
A single-file solution that:
1) Loads credentials for dsbmobile.com (from .env or OS).
2) Scrapes the "DaVinci Touch" section for class/course replacements.
3) Saves raw data to a JSON file only if changes are detected.
4) Formats that JSON data into a final structure.
5) Replaces teacher codes with full names from lehrer.json
6) Validates the final JSON with a JSON schema.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

import jsonschema
import requests
from bs4 import BeautifulSoup
from dotenv import dotenv_values
from rich_argparse import RawDescriptionRichHelpFormatter

# Logging from external file
from logger_setup import LoggerSetup
from PyDSB import PyDSB

# -----------------------------------------------------------
# 1) Logger Setup
# -----------------------------------------------------------
logger = LoggerSetup.setup_logger("UnifiedScraper")


# -----------------------------------------------------------
# 2) Environment + Credential Handling
# -----------------------------------------------------------
class EnvCredentialsLoader:
    """
    Loads dsbmobile.com credentials from a .env file or OS environment variables,
    with data hiding of internal attributes and methods.
    """

    def __init__(self, env_file: str):
        """
        Initialize with a path to the .env file, stored privately.
        """
        self.__env_file = env_file
        self.__logger = LoggerSetup.setup_logger(self.__class__.__name__)
        self.__credentials: Dict[str, str] = {}

    def __mask_string(self, s: str) -> str:
        """
        Private helper to mask all but the first three characters of a string.
        """
        if len(s) <= 3:
            return s
        return s[:3] + "*" * (len(s) - 3)

    def load_env_credentials(self) -> Dict[str, str]:
        """
        Public method to load environment credentials from .env or OS environment variables.

        Returns:
            Dict[str, str]: Dictionary with 'DSB_USERNAME' and 'DSB_PASSWORD'.

        Raises:
            ValueError: If credentials are missing or not found.
        """
        try:
            env_values = dotenv_values(self.__env_file)
            if env_values and "DSB_USERNAME" in env_values and "DSB_PASSWORD" in env_values:
                dsb_username = env_values["DSB_USERNAME"]
                dsb_password = env_values["DSB_PASSWORD"]
                if not dsb_username or not dsb_password:
                    raise ValueError("DSB_USERNAME or DSB_PASSWORD is empty.")
                self.__credentials = {
                    "DSB_USERNAME": dsb_username,
                    "DSB_PASSWORD": dsb_password
                }
                self.__logger.info("Loaded credentials from .env file.")
            else:
                raise ValueError("DSB_USERNAME/DSB_PASSWORD not found in .env")
        except (FileNotFoundError, ValueError) as exc:
            self.__logger.warning("Failed to load credentials from .env, attempting OS environment...")
            dsb_username = os.getenv("DSB_USERNAME")
            dsb_password = os.getenv("DSB_PASSWORD")
            if not dsb_username or not dsb_password:
                raise ValueError(
                    "DSB_USERNAME and DSB_PASSWORD must be set."
                ) from exc
            self.__credentials = {
                "DSB_USERNAME": dsb_username,
                "DSB_PASSWORD": dsb_password
            }

        # Log masked credentials
        self.__logger.info(
            "Using Username: %s, Password: %s",
            self.__mask_string(self.__credentials["DSB_USERNAME"]),
            self.__mask_string(self.__credentials["DSB_PASSWORD"])
        )
        return self.__credentials


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

    def __init__(self, username: str, password: str, log_level):
        self.username = username
        self.password = password
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)

    def prepare_api_url(self) -> str:
        """
        Fetch the 'DaVinci Touch' URL from the postings list using PyDSB.
        Raises ValueError if not found.
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
        Parse the base URL to find all day-index plan links (like 'Montag_01-01-2024': 'url').
        """
        soup = self._request_url_data(base_url)
        posts_dict = {}

        try:
            day_index = soup.find("ul", class_="day-index")
            if not day_index:
                self.logger.warning("No 'ul.day-index' found. Possibly no plans available.")
                return posts_dict
            links = day_index.find_all("a")  # type: ignore

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
                    full_url = requests.compat.urljoin(base_url, href)  # type: ignore
                    posts_dict[new_key] = full_url
                    self.logger.debug("Found plan: %s -> %s", new_key, full_url)
                else:
                    self.logger.warning("Unexpected link text format: '%s'. Skipped.", text)
        except AttributeError as e:
            self.logger.error("Error parsing HTML structure for day-index: %s", e)
            raise

        return posts_dict

    def _scrape_single_plan(self, plan_url: str, course: str) -> Tuple[List[List[str]], bool]:
        """
        Given a plan URL, find all rows in <table> that match 'course' in the first column,
        plus subsequent rows that contain \xa0 in the first column.
        """
        soup = self._request_url_data(plan_url)
        success = False
        total_replacements: List[List[str]] = []

        try:
            table = soup.find("table")
            if not table:
                raise ValueError("Table element not found in HTML.")

            rows = table.find_all("tr")  # type: ignore
            for row in rows:
                columns = row.find_all("td")
                if not columns:
                    continue

                # If first cell matches the course, gather that row & subsequent
                if columns[0].get_text(strip=True) == course:
                    success = True
                    self.logger.debug("Course '%s' found in row: %s", course, row)
                    replacement = [col.get_text(strip=True) for col in columns]
                    total_replacements.append(replacement)

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
        Loop through each day-indexed plan (URL), parse for matching 'course' rows.
        If print_output = True, it logs the raw dictionary as JSON.
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
        Compare new_data to existing file content. If unchanged, skip. Otherwise, save.
        Returns a bool indicating if changes were detected and saved.
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
    Builds a final structured JSON from the raw data, grouping by day, generating content lists, etc.
    """

    def __init__(self, log_level: int):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)
        self.weekday_map = {
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
        self.entry_counter += 1
        iso_weekday_num = self.weekday_map.get(weekday, 0)

        substitution_entry = {
            "id": str(self.entry_counter),
            "date": date,
            "weekDay": [str(iso_weekday_num), weekday],
            "content": []
        }

        last_position = None
        for entry in entries:
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
        self, scraped_data: Dict[str, List[List[str]]], course: str
    ) -> Dict[str, Any]:
        """
        Create a final structured JSON from the raw data.
        """
        output = {
            "createdAt": datetime.now().isoformat(),
            "class": course,
            "substitution": []
        }

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
    Validates the final JSON data against a schema if provided.
    """

    def __init__(self):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__)

    def validate(self, json_data: dict, schema_file: str) -> None:
        try:
            with open(schema_file, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            jsonschema.validate(instance=json_data, schema=schema)
            self.logger.info("JSON data is valid according to '%s'.", schema_file)
        except jsonschema.exceptions.ValidationError as e:
            self.logger.error("JSON data is invalid: %s", e.message)
            raise


# -----------------------------------------------------------
# 6) TEACHER REPLACER CLASS
# -----------------------------------------------------------
class TeacherReplacer:
    """
    Replaces teacher codes in a data structure, given a mapping from teacher codes to names.
    """

    def __init__(self, log_level):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)

    def replace_teacher_codes(self, data: Dict[str, Any], teacher_mapping: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        """
        For each teacher code found in 'teacher', replace with the teacher's last name (or 'Nachname')
        from teacher_mapping. If the original code was in parentheses, preserve them.
        """
        counter: int = 0
        for substitution in data.get("substitution", []):
            for item in substitution.get("content", []):
                if "teacher" in item:
                    code = item["teacher"]
                    clean_code = code.strip('()')
                    if clean_code in teacher_mapping:
                        old_value = item["teacher"]
                        name = teacher_mapping[clean_code]['Nachname']
                        # If code had parentheses, keep them
                        item["teacher"] = f"({name})" if code.startswith("(") else name
                        self.logger.debug("CHANGE: teacher: changed '%s' to '%s'", old_value, item["teacher"])
                        counter += 1
        self.logger.info("Replaced \033[1m%d\033[0m teacher codes.", counter)
        return data


# -----------------------------------------------------------
# 7) CLI + Main Orchestrator
# -----------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for the script using RichArgParse for ASCII art, etc.
    """
    ascii_art = r"""
     ___      ___  ___ ___
    | _ \_  _|   \/ __| _ )
    |  _/ || | |) \__ \ _ \
    |_|  \_, |___/|___/___/
         |__/
    """
    parser = argparse.ArgumentParser(
        prog="python scraper.py",
        description=ascii_art +
        "\nScrape data from dsbmobile.com to retrieve class replacements.",
        formatter_class=RawDescriptionRichHelpFormatter)

    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable DEBUG logging and disable cache"
    )
    parser.add_argument(
        "-c", "--course", default="MSS12",
        help="Which course to scrape. Default: MSS12"
    )
    parser.add_argument(
        "--env-file", default=".env",
        help="Path to the .env file. Default: .env"
    )
    parser.add_argument(
        "-p", "--print-output", action="store_true",
        help="Print raw JSON output after scraping."
    )
    parser.add_argument(
        "-o", "--output-dir", default="json/formatted.json",
        help="Path for the formatted JSON output. Default: json/formatted.json"
    )
    parser.add_argument(
        "--raw-file", default="json/scraped.json",
        help="Path for the raw scraped JSON data. Default: json/scraped.json"
    )
    parser.add_argument(
        "--schema-file", default="schema/schema.json",
        help="Path to the JSON schema file. Default: schema/schema.json"
    )
    parser.add_argument(
        "--teacher-file", default="schema/lehrer.json",
        help="Path to the teacher mapping file. Default: schema/lehrer.json"
    )
    parser.add_argument(
        "--teacher-replaced-file", default="json/teacher_replaced.json",
        help="Output file after teacher code replacement. Default: json/teacher_replaced.json"
    )
    return parser.parse_args()


def main():
    """
    Main entry point. Ties together:
      - Credentials loading
      - Scraping
      - Saving raw data
      - Formatting
      - Teacher code replacement
      - Validation
      - Respecting CLI arguments for paths, course, print output, etc.
    """
    args = parse_arguments()

    # Set log level (DEBUG if -v, else INFO)
    log_level: int = logging.DEBUG if args.verbose else logging.INFO
    LoggerSetup.setup_logger("UnifiedScraper", log_level)

    logger.info("Starting unified DSB scraping process...")
    logger.debug("Parsed arguments: %s", args)

    # Step 1: Load credentials
    creds_loader = EnvCredentialsLoader(args.env_file)
    try:
        creds = creds_loader.load_env_credentials()
    except ValueError as e:
        logger.critical("Could not load credentials: %s", e)
        sys.exit(1)

    # Step 2: Scrape
    scraper = DSBScraper(creds["DSB_USERNAME"], creds["DSB_PASSWORD"], log_level)
    try:
        base_url = scraper.prepare_api_url()
    except Exception as e:
        logger.critical("Failed to prepare API URL: %s", e)
        sys.exit(1)

    plans_dict = scraper.get_plans(base_url)
    raw_data = scraper.scrape_all_plans(plans_dict, args.course, args.print_output)

    # Step 3: Compare & Save raw JSON if changed
    if args.verbose:
        changes_detected = True
    else:
        changes_detected = scraper.save_data_if_changed(raw_data, args.raw_file)

    if not changes_detected:
        logger.info("No changes detected; exiting early.")
        sys.exit(0)

    # Step 4: Format JSON
    formatter = JSONFormatter(log_level)
    final_json = formatter.format_data(raw_data, args.course)

    # Write formatted JSON
    os.makedirs(os.path.dirname(args.output_dir), exist_ok=True)
    try:
        with open(args.output_dir, "w", encoding="utf-8") as f:
            json.dump(final_json, f, ensure_ascii=False, indent=4)
        logger.info("Formatted data saved to '%s'.", args.output_dir)
    except Exception as e:
        logger.error("Error saving formatted JSON: %s", e)

    # Step 5: Load teacher mapping & replace teacher codes
    replacer = TeacherReplacer(log_level)
    try:
        with open(args.teacher_file, "r", encoding="utf-8") as tfile:
            teacher_map = json.load(tfile)
        replaced_data = replacer.replace_teacher_codes(final_json, teacher_map)
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
