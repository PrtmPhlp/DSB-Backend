#!/usr/bin/env python3
# -----------------------------------------------------------
"""
A single-file solution that:

1) Loads credentials from a .env file or OS environment variables.
2) Scrapes multiple courses from dsbmobile.com (DaVinci Touch) in parallel.
3) Parses all table rows and merges sub-lines with empty first column into the last encountered course.
4) Saves raw day-based data if changed.
5) Formats that data into a multi-course JSON structure.
6) Replaces teacher codes.
7) Validates the final JSON with a JSON schema (optionally).
"""

import argparse
import concurrent.futures
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import jsonschema
import requests
from bs4 import BeautifulSoup
from dotenv import dotenv_values
from rich_argparse import RawDescriptionRichHelpFormatter

# Logging from external file
from logger_setup import LoggerSetup
from PyDSB import PyDSB

# ---------------------------------------------------------------------------
# 1) Logger Setup
# ---------------------------------------------------------------------------
logger = LoggerSetup.setup_logger("UnifiedScraper")


# ---------------------------------------------------------------------------
# 2) Environment + Credential Handling
# ---------------------------------------------------------------------------
class EnvCredentialsLoader:
    """
    Loads dsbmobile.com credentials from a .env file or OS environment variables.
    """

    def __init__(self, env_file: str):
        self.__env_file = env_file
        self.__logger = LoggerSetup.setup_logger(self.__class__.__name__)
        self.__credentials: Dict[str, str] = {}

    def __mask_string(self, s: str) -> str:
        if len(s) <= 3:
            return s
        return s[:3] + "*" * (len(s) - 3)

    def load_env_credentials(self) -> Dict[str, str]:
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
        except (FileNotFoundError, ValueError):
            self.__logger.warning("Failed to load credentials from .env, attempting OS environment...")
            dsb_username = os.getenv("DSB_USERNAME")
            dsb_password = os.getenv("DSB_PASSWORD")
            if not dsb_username or not dsb_password:
                raise ValueError("DSB_USERNAME and DSB_PASSWORD must be set.")
            self.__credentials = {
                "DSB_USERNAME": dsb_username,
                "DSB_PASSWORD": dsb_password
            }

        self.__logger.info(
            "Using Username: %s, Password: %s",
            self.__mask_string(self.__credentials["DSB_USERNAME"]),
            self.__mask_string(self.__credentials["DSB_PASSWORD"])
        )
        return self.__credentials


# ---------------------------------------------------------------------------
# 3) DSBScraper: Requests handling + Day-based parsing
# ---------------------------------------------------------------------------
class DSBScraper:
    """
    Scrapes day-plans once per day. Each day-plan's HTML is fetched in parallel,
    then we parse its <table> and distribute lines to the correct course.
    Sub-lines with an empty first column are attached to the previously encountered course.
    """

    def __init__(self, username: str, password: str, log_level: int):
        self.username = username
        self.password = password
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)

    def prepare_api_url(self) -> str:
        """Fetch the 'DaVinci Touch' URL from dsbmobile.com postings."""
        self.logger.info("Attempting to fetch postings via PyDSB.")
        try:
            dsb = PyDSB(self.username, self.password)
            data = dsb.get_postings()
        except requests.ConnectionError as e:
            self.logger.critical("No Internet Connection: %s", e)
            raise

        for section in data:
            if section["title"] == "DaVinci Touch":
                base_url = section["url"]
                self.logger.debug("DaVinci Touch URL found: %s", base_url)
                return base_url

        raise ValueError("DaVinci Touch section not found in postings.")

    def _fetch_day_html(self, url: str) -> BeautifulSoup:
        """Request one day's HTML once, forcing UTF-8 to fix 'RaumÃ¤nderung' issues."""
        self.logger.debug("Requesting day-plan HTML: %s", url)
        response = requests.get(url, timeout=10)
        response.encoding = "utf-8"  # Force UTF-8 decoding
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            self.logger.critical("HTTP server error occurred: %s", e)
            raise
        return BeautifulSoup(response.text, "html.parser")

    def get_day_plans(self, base_url: str) -> Dict[str, str]:
        """
        Return a dict day_key -> day_url, e.g. {"Montag_10-03-2025": "http://..."}
        """
        day_plans: Dict[str, str] = {}

        soup = self._fetch_day_html(base_url)
        day_index = soup.find("ul", class_="day-index")
        if not day_index:
            self.logger.warning("No <ul class='day-index'> found at DaVinci Touch URL.")
            return day_plans

        a_tags = day_index.find_all("a")  # type: ignore
        for a_tag in a_tags:
            href = a_tag.get("href")
            text = a_tag.get_text(strip=True)
            parts = text.split()
            if len(parts) == 2:
                date_str, weekday_str = parts
                day_key = f"{weekday_str}_{date_str.replace('.', '-')}"
                full_url = requests.compat.urljoin(base_url, href)  # type: ignore
                day_plans[day_key] = full_url
                self.logger.debug("Found day-plan link: %s -> %s", day_key, full_url)
            else:
                self.logger.warning("Unexpected day link text: '%s'", text)

        return day_plans

    def parse_single_day(self, day_key: str, day_url: str) -> Dict[str, List[List[str]]]:
        """
        Parse the HTML table for one day. Lines whose first column is empty (or \xa0) are 
        attached to the *previously encountered* course. This prevents an empty "" course.
        Returns a dict: { "5a": [[row], [row]], "MSS12": [[row], ...], ... }
        """
        day_data: Dict[str, List[List[str]]] = {}
        soup = self._fetch_day_html(day_url)
        table = soup.find("table")

        if not table:
            self.logger.warning("No <table> found for day '%s' at %s", day_key, day_url)
            return day_data

        last_course = None
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if not cols:
                continue

            first_cell = cols[0].get_text(strip=True)

            # If first cell is empty or \xa0 => attach to last_course (continuation line)
            # Otherwise, we update last_course to the new course
            if first_cell == "" or first_cell == "\xa0":
                # continuation line
                if last_course is None:
                    # If there's no previously encountered course, skip or treat as unknown
                    self.logger.debug(
                        "Row with empty first cell encountered before any course. Skipping row: %s",
                        [c.get_text(strip=True) for c in cols]
                    )
                    continue
                course_name = last_course
            else:
                # new course
                course_name = first_cell
                last_course = course_name

            # Gather the entire row
            row_values = [c.get_text(strip=True) for c in cols]

            if course_name not in day_data:
                day_data[course_name] = []
            day_data[course_name].append(row_values)

        return day_data

    def scrape_all_days_once(self, base_url: str) -> Dict[str, Dict[str, List[List[str]]]]:
        """
        1) get_day_plans -> day_key -> day_url
        2) For each day, parse once -> day_data => {course: [[rows]]}
        3) Combine them into raw_data[day_key][course] = [ rows... ]
        """
        raw_data: Dict[str, Dict[str, List[List[str]]]] = {}
        day_plans = self.get_day_plans(base_url)
        if not day_plans:
            self.logger.warning("No day plans found. raw_data will be empty.")
            return raw_data

        self.logger.debug("Scraping each day-plan in parallel (single request per day).")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_map = {
                executor.submit(self.parse_single_day, dk, du): dk
                for dk, du in day_plans.items()
            }
            for fut in concurrent.futures.as_completed(future_map):
                day_key = future_map[fut]
                try:
                    day_data = fut.result()
                    raw_data[day_key] = day_data
                except Exception as e:
                    self.logger.error("Error parsing day '%s': %s", day_key, e)
                    raw_data[day_key] = {}

        return raw_data

    def save_data_if_changed(self, data: Dict[str, Any], file_path: str, skip_validator: bool) -> bool:
        existing_data = None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        if existing_data == data and skip_validator is False:
            self.logger.info("No changes detected. Skipping save.")
            return False
        elif skip_validator:
            self.logger.warning("Raw Data validation skipped via --skip-validator")

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info("Saved raw day-based data to %s", file_path)
        return True


# -------------------------------------------------------------------
# 4) JSONFormatter: Inverting day-based data to multi-course format.
# -------------------------------------------------------------------
class JSONFormatter:
    """
    Inverts day-based data to a multi-course structure.
    Each day_key => {course_name => list-of-rows} becomes "courses" -> day-based "substitution".
    Also merges lines that had no first column into the correct course, so no empty "" course.
    """

    def __init__(self, log_level: int):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)
        self.entry_id = 0

    def _make_substitution_entry(self, day_key: str, rows: List[List[str]]) -> Dict[str, Any]:
        """Build a single 'substitution' item for a single day_key & course's rows."""
        self.entry_id += 1
        parts = day_key.split("_", 1)
        if len(parts) == 2:
            weekday_str, date_str = parts
        else:
            weekday_str, date_str = (day_key, "")

        sub = {
            "id": str(self.entry_id),
            "date": date_str,
            "weekDay": [weekday_str],
            "content": []
        }

        last_position = None
        for row in rows:
            # row structure: [course, position, teacher, subject, room, topic, info, ...]
            position = row[1] if len(row) > 1 else ""
            if position == "":
                position = last_position

            content_piece = {
                "position": position or "",
                "teacher": row[2] if len(row) > 2 else "",
                "subject": row[3] if len(row) > 3 else "",
                "room":    row[4] if len(row) > 4 else "",
                "topic":   row[5] if len(row) > 5 else "",
                "info":    row[6] if len(row) > 6 else ""
            }
            if position:
                last_position = position

            sub["content"].append(content_piece)

        return sub

    def format_data(self, day_based_data: Dict[str, Dict[str, List[List[str]]]]) -> Dict[str, Any]:
        """
        Turn day-based data into:
          {
            "createdAt": "...",
            "courses": {
              "5a": { "substitution": [ day_sub1, day_sub2, ... ] },
              "MSS12": ...
            }
          }
        """
        final = {
            "createdAt": datetime.now().isoformat(),
            "courses": {}
        }
        # Collect all courses from all days
        all_courses = set()
        for day_key, course_map in day_based_data.items():
            for course_name in course_map.keys():
                all_courses.add(course_name)

        # Build final "courses" -> "substitution" for each course
        for course_name in sorted(all_courses):
            # We'll accumulate day-based substitution entries
            substitutions = []
            self.entry_id = 0
            # For day_key in sorted order to keep them stable
            for day_key in sorted(day_based_data.keys()):
                course_rows = day_based_data[day_key].get(course_name, [])
                if course_rows:
                    sub_entry = self._make_substitution_entry(day_key, course_rows)
                    substitutions.append(sub_entry)

            final["courses"][course_name] = {"substitution": substitutions}

        return final

    def save_data(self, data: Dict[str, Any], file_path: str) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info("Formatted multi-course data saved to %s", file_path)


# -------------------------------------------------------------------
# 5) TeacherReplacer
# -------------------------------------------------------------------
class TeacherReplacer:
    """
    Replaces teacher codes for every course in the final data structure.
    Then overwrites the file with the replaced data.
    """

    def __init__(self, log_level: int):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)

    def replace_teacher_codes(self, final_data: Dict[str, Any], teacher_map: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
        courses = final_data.get("courses", {})
        total_changes = 0

        for course_name, course_obj in courses.items():
            subs = course_obj.get("substitution", [])
            for sub in subs:
                for item in sub.get("content", []):
                    code = item.get("teacher", "")
                    clean_code = code.strip('()')
                    if clean_code in teacher_map:
                        old_val = code
                        name = teacher_map[clean_code]["Nachname"]
                        item["teacher"] = f"({name})" if code.startswith("(") else name
                        self.logger.debug("Changed teacher '%s' -> '%s'", old_val, item["teacher"])
                        total_changes += 1

        self.logger.info("Replaced %d teacher codes across all courses.", total_changes)
        return final_data

    def save_data(self, replaced_data: Dict[str, Any], path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(replaced_data, f, indent=2, ensure_ascii=False)
        self.logger.info("Teacher-replaced multi-course data saved to %s", path)


# -------------------------------------------------------------------
# 6) JSONSchemaValidator
# -------------------------------------------------------------------
class JSONSchemaValidator:
    """
    Validates the final JSON data against a JSON schema.
    """
    def __init__(self):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__)

    def validate(self, data: Dict[str, Any], schema_path: str, skip_validator: bool) -> bool:
        if skip_validator:
            self.logger.warning("JSON schema validation skipped via --skip-validator")
            return False
        try:
            with open(schema_path, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            jsonschema.validate(instance=data, schema=schema)
            self.logger.info("JSON data is valid according to '%s'.", schema_path)
            return True
        except FileNotFoundError:
            self.logger.warning("Schema file '%s' not found; skipping schema validation.", schema_path)
            return False
        except jsonschema.exceptions.ValidationError as e:
            self.logger.error("JSON data is invalid: %s", e.message)
            raise


# -------------------------------------------------------------------
# 7) CLI + Main Orchestrator
# -------------------------------------------------------------------
def parse_arguments() -> argparse.Namespace:
    ascii_art = r"""
     ___      ___  ___ ___
    | _ \_  _|   \/ __| _ )
    |  _/ || | |) \__ \ _ \
    |_|  \_, |___/|___/___/
         |__/
    """
    parser = argparse.ArgumentParser(
        prog="python scraper.py",
        description=ascii_art + "\nScrape day-plans once per day, attach empty-first-column lines to the last course.",
        formatter_class=RawDescriptionRichHelpFormatter
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging.")
    parser.add_argument("--env-file", default=".env", help="Path to the .env file.")
    parser.add_argument("--raw-file", default="json/scraped.json", help="Where to save the raw day-based data.")
    parser.add_argument("--output-formatted-file", default="json/formatted.json", help="Where to save the formatted multi-course JSON.")
    parser.add_argument("--teacher-dict", default="schema/lehrer.json", help="Path to the teacher dictionary file.")
    parser.add_argument("--teacher-replaced-file", default="json/teacher_replaced.json", help="Where to save the teacher-replaced JSON.")
    parser.add_argument("--schema-file", default="schema/schema.json", help="Path to the JSON schema file.")
    parser.add_argument("--skip-validator", action="store_true", help="Skip JSON schema validation.")
    parser.add_argument("-p", "--print-output", action="store_true", help="Print raw day-based JSON output.")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Logging level
    log_level = logging.DEBUG if args.verbose else logging.INFO
    LoggerSetup.setup_logger("UnifiedScraper", log_level)

    logger.info("Starting multi-course DSB scraping process...")
    logger.debug("Parsed arguments: %s", args)

    # 1) Credentials
    creds_loader = EnvCredentialsLoader(args.env_file)
    try:
        creds = creds_loader.load_env_credentials()
    except ValueError as e:
        logger.critical("Could not load credentials: %s", e)
        sys.exit(1)

    # 2) Prepare
    scraper = DSBScraper(creds["DSB_USERNAME"], creds["DSB_PASSWORD"], log_level)
    try:
        base_url = scraper.prepare_api_url()
    except Exception as e:
        logger.critical("Failed to retrieve DaVinci Touch URL: %s", e)
        sys.exit(1)

    # 3) Day-based parse: single fetch per day
    day_data = scraper.scrape_all_days_once(base_url)
    if args.print_output:
        raw_json = json.dumps(day_data, indent=2, ensure_ascii=False)
        logger.info("Raw day-based data:\n%s", raw_json)

    # 4) Save if changed
    changed = scraper.save_data_if_changed(day_data, args.raw_file, args.skip_validator)
    if not changed:
        logger.info("No changes detected in raw data. Exiting early.")
        sys.exit(0)

    # 5) Format day-based data -> multi-course
    formatter = JSONFormatter(log_level)
    final_data = formatter.format_data(day_data)
    formatter.save_data(final_data, args.output_formatted_file)

    # 6) Teacher replacement
    replacer = TeacherReplacer(log_level)
    try:
        with open(args.teacher_dict, "r", encoding="utf-8") as tf:
            teacher_map = json.load(tf)
        replaced_data = replacer.replace_teacher_codes(final_data, teacher_map)
        replacer.save_data(replaced_data, args.teacher_replaced_file)
    except FileNotFoundError:
        logger.warning("Teacher file '%s' not found; skipping teacher code replacement.", args.teacher_dict)
        replaced_data = final_data
    except Exception as e:
        logger.error("Teacher replacement error: %s", e)
        replaced_data = final_data

    # 7) Validate (skippable via --skip-validator)
    validator = JSONSchemaValidator()
    validator.validate(replaced_data, args.schema_file, args.skip_validator)

    logger.info("All multi-course scraping steps complete. Exiting.")


if __name__ == "__main__":
    main()
