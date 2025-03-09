#!/usr/bin/env python3
# -----------------------------------------------------------
"""
A single-file solution that:
1) Loads credentials from a .env file or OS environment variables.
2) Scrapes multiple courses from dsbmobile.com (DaVinci Touch) in parallel.
3) Merges their raw data into one structure; saves if changed.
4) Formats that data into a combined final JSON.
5) Replaces teacher codes with teacher mapping.
6) Validates the final JSON with a JSON schema.

Usage:
  python scraper.py
  python scraper.py --verbose
"""

import argparse
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

# -------------------------------------------------------------------
# 1) Logger Setup
# -------------------------------------------------------------------
logger = LoggerSetup.setup_logger("UnifiedScraper")

# -------------------------------------------------------------------
# 2) Environment + Credential Handling
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# 3) DSBScraper
# -------------------------------------------------------------------
class DSBScraper:
    """
    Encapsulates logic to:
      - Fetch data from dsbmobile.com (DaVinci Touch)
      - Parse relevant HTML
      - Compare changes and save to JSON (only if changed)
    """
    def __init__(self, username: str, password: str, log_level: int):
        self.username = username
        self.password = password
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)

    def prepare_api_url(self) -> str:
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

    def _request_url_data(self, url: str) -> BeautifulSoup:
        self.logger.debug("Requesting data from URL: %s", url)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")

    def get_plans(self, base_url: str) -> Dict[str, str]:
        soup = self._request_url_data(base_url)
        posts_dict = {}

        day_index = soup.find("ul", class_="day-index")
        if not day_index:
            self.logger.warning("No 'ul.day-index' found.")
            return posts_dict

        links = day_index.find_all("a")  # type: ignore
        if not links:
            self.logger.warning("No <a> tags found in day-index.")
            return posts_dict

        href_links = [link.get("href") for link in links]
        text_list = [link.get_text(strip=True) for link in links]

        for href, text in zip(href_links, text_list):
            parts = text.split()
            if len(parts) == 2:
                date_str, weekday_str = parts[0], parts[1]
                new_key = f"{weekday_str}_{date_str.replace('.', '-')}"
                full_url = requests.compat.urljoin(base_url, href)  # type: ignore
                posts_dict[new_key] = full_url
                self.logger.debug("Found plan: %s -> %s", new_key, full_url)
            else:
                self.logger.warning("Unexpected link format: '%s'", text)

        return posts_dict

    def _scrape_single_plan(self, plan_url: str, course: str) -> Dict[str, List[List[str]]]:
        """
        Returns a dict: { day_key: [table rows], ... } but here we just handle one day at a time.
        Actually we'll build a minimal structure in code below. For now let's just store the raw row data.
        """
        self.logger.debug("Scraping plan for course '%s' at URL: %s", course, plan_url)
        data_rows: List[List[str]] = []
        success = False

        soup = self._request_url_data(plan_url)
        table = soup.find("table")
        if not table:
            raise ValueError("Table element not found in HTML.")

        rows = table.find_all("tr")  # type: ignore
        for row in rows:
            columns = row.find_all("td")
            if not columns:
                continue

            if columns[0].get_text(strip=True) == course:
                success = True
                replacement = [col.get_text(strip=True) for col in columns]
                data_rows.append(replacement)

                next_row = row.find_next_sibling("tr")
                while next_row and "\xa0" in next_row.find("td").get_text():
                    columns_next = next_row.find_all("td")
                    rep_next = [col.get_text(strip=True) for col in columns_next]
                    data_rows.append(rep_next)
                    next_row = next_row.find_next_sibling("tr")

        # Return a dict with a single key for later merging
        return {"rows": data_rows, "found": success}

    def scrape_course(self, base_url: str, course: str, print_output: bool = False) -> Dict[str, Any]:
        """
        Scrape all day-index plans from base_url for a specific course.
        Return a dictionary of day_key -> rows, i.e. the raw data for this course.
        """
        plans_dict = self.get_plans(base_url)
        course_data = {}
        for day_key, url in plans_dict.items():
            single_data = self._scrape_single_plan(url, course)
            course_data[day_key] = single_data["rows"]

        if print_output:
            pretty_json = json.dumps(course_data, indent=2, ensure_ascii=False)
            self.logger.info("Scrape Result for course %s:\n%s", course, pretty_json)

        return course_data

    def save_data_if_changed(self, data: Dict[str, Any], file_path: str, verbose) -> bool:
        existing = None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        if existing == data and verbose is False:
            self.logger.info("No changes detected. Skipping save.")
            return False

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info("Saved combined raw data to %s", file_path)
        return True

# -------------------------------------------------------------------
# 4) JSONFormatter
# -------------------------------------------------------------------
class JSONFormatter:
    def __init__(self, log_level: int):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__, log_level)

    def format_data(self, raw_data: Dict[str, Dict[str, List[List[str]]]]) -> Dict[str, Any]:
        """
        Combine all courses into a single structure:
            {
              "createdAt": "...",
              "courses": {
                "5a": { "substitution": [...], ... },
                "5b": { ... },
                ...
              }
            }
        """
        output = {
            "createdAt": datetime.now().isoformat(),
            "courses": {}
        }

        for course_name, day_dict in raw_data.items():
            # Each 'day_dict' is { "Montag_01-09-2024": [[row1], [row2], ... ], ... }
            # Transform it into { "substitution": [ ... ] }
            # or create 'substitution' from each day
            course_substitutions = []
            substitution_id = 1

            for day_key, rows in day_dict.items():
                if "_" not in day_key:
                    self.logger.warning("Unexpected day_key format: %s", day_key)
                    continue

                weekday_str, date_str = day_key.split("_", 1)
                sub_entry = {
                    "id": str(substitution_id),
                    "date": date_str,
                    "weekDay": [weekday_str],  # or more robust logic
                    "content": []
                }

                last_position = None
                for row in rows:
                    # row is [course, position, teacher, subject, ...]
                    # or maybe fewer columns
                    position = row[1] if len(row) > 1 else None
                    if position == "":
                        position = last_position

                    content_piece = {
                        "position": position if position else "",
                        "teacher": row[2] if len(row) > 2 else "",
                        "subject": row[3] if len(row) > 3 else "",
                        "room":    row[4] if len(row) > 4 else "",
                        "topic":   row[5] if len(row) > 5 else "",
                        "info":    row[6] if len(row) > 6 else ""
                    }
                    if position:
                        last_position = position

                    sub_entry["content"].append(content_piece)

                course_substitutions.append(sub_entry)
                substitution_id += 1

            output["courses"][course_name] = {
                "substitution": course_substitutions
            }

        return output

    def save_data(self, formatted_data: Dict[str, Any], path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(formatted_data, f, indent=2, ensure_ascii=False)
        self.logger.info("Formatted multi-course data saved to %s", path)

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
                    if "teacher" in item:
                        code = item["teacher"]
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
    def __init__(self):
        self.logger = LoggerSetup.setup_logger(self.__class__.__name__)

    def validate(self, data: Dict[str, Any], schema_path: str) -> None:
        try:
            with open(schema_path, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            jsonschema.validate(instance=data, schema=schema)
            self.logger.info("JSON data is valid according to '%s'.", schema_path)
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
        description=ascii_art + "\nScrape data from dsbmobile.com for multiple courses in parallel.",
        formatter_class=RawDescriptionRichHelpFormatter
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging, always try to save JSON")
    parser.add_argument("--env-file", default=".env", help="Path to the .env file. Default: .env")
    parser.add_argument("-p", "--print-output", action="store_true", help="Print raw JSON output after scraping.")
    parser.add_argument("--raw-file", default="json/scraped.json", help="Path for combined raw data. Default: json/scraped.json")
    parser.add_argument("--output-dir", default="json/formatted.json", help="Where to save the formatted JSON. Default: json/formatted.json")
    parser.add_argument("--teacher-file", default="schema/lehrer.json", help="Path to the teacher mapping file.")
    parser.add_argument("--teacher-replaced-file", default="json/teacher_replaced.json", help="Where to save teacher-replaced JSON.")
    parser.add_argument("--schema-file", default="schema/schema.json", help="JSON schema path.")
    parser.add_argument("--skip-validator", action="store_true", help="Skip JSON schema validation.")
    return parser.parse_args()


def main():
    args = parse_arguments()

    # We define the default multi-courses to scrape
    courses_to_scrape = ["5a", "5b", "5c", "MSS11", "MSS12"]

    # Set log level
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

    # 2) Prepare base URL (DaVinci Touch)
    scraper = DSBScraper(creds["DSB_USERNAME"], creds["DSB_PASSWORD"], log_level)
    try:
        base_url = scraper.prepare_api_url()
    except Exception as e:
        logger.critical("Failed to prepare API URL: %s", e)
        sys.exit(1)

    # 3) Scrape each course in parallel, gather results
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def scrape_single_course(course: str) -> Dict[str, Any]:
        """
        Helper that uses the scraper instance to retrieve raw data for a single course.
        """
        return scraper.scrape_course(base_url, course, args.print_output)

    # Store results in a dictionary: { "5a": { day1: [...], day2: [...] }, ... }
    all_raw_data: Dict[str, Dict[str, List[List[str]]]] = {}

    with ThreadPoolExecutor() as executor:
        future_to_course = {
            executor.submit(scrape_single_course, c): c
            for c in courses_to_scrape
        }
        for future in as_completed(future_to_course):
            course_name = future_to_course[future]
            try:
                data_for_course = future.result()
                all_raw_data[course_name] = data_for_course
            except Exception as exc:
                logger.error("Course '%s' generated an exception: %s", course_name, exc)
                all_raw_data[course_name] = {}

    # 4) Save combined raw data if changed
    changes_detected = scraper.save_data_if_changed(all_raw_data, args.raw_file, args.verbose)
    if not changes_detected:
        logger.info("No changes detected in raw data. Exiting early.")
        sys.exit(0)

    # 5) Format the combined data
    formatter = JSONFormatter(log_level)
    formatted_data = formatter.format_data(all_raw_data)
    formatter.save_data(formatted_data, args.output_dir)

    # 6) Teacher replacement
    replacer = TeacherReplacer(log_level)
    try:
        with open(args.teacher_file, "r", encoding="utf-8") as tf:
            teacher_map = json.load(tf)
        replaced_data = replacer.replace_teacher_codes(formatted_data, teacher_map)
    except FileNotFoundError:
        logger.warning("Teacher file '%s' not found; skipping teacher code replacement.", args.teacher_file)
        replaced_data = formatted_data
    except Exception as e:
        logger.error("Error in teacher replacement: %s", e)
        replaced_data = formatted_data

    replacer.save_data(replaced_data, args.teacher_replaced_file)

    # 7) Validate only if not skipped
    if not args.skip_validator:
        validator = JSONSchemaValidator()
        try:
            validator.validate(replaced_data, args.schema_file)
        except jsonschema.exceptions.ValidationError:
            logger.critical("Validation failed. Exiting.")
            sys.exit(1)
    else:
        logger.warning("Skipping JSON schema validation.")

    logger.info("All multi-course scraping steps complete. Exiting.")


if __name__ == "__main__":
    main()
