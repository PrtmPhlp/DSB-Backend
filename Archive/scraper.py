#!/usr/bin/env python3
# ------------------------------------------------
"""
This script scrapes data from dsbmobile.com to retrieve class replacements.
The scraped data is then organized and saved to a JSON file.

__author__ = "PrtmPhlp"
__Contact__ = "contact@pertermann.de"
__Status__ = "Development"
"""
# ------------------------------------------------
# ! Imports

import argparse
import json
import logging
from os import getenv
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dotenv import dotenv_values

from logger import setup_logger
from PyDSB import PyDSB

# Initialize logger
logger = setup_logger(__name__)


def load_env_credentials() -> dict[str, str | None]:
    """
    Load environment credentials from a .env file.

    Returns:
        dict: A dictionary containing the environment variables.

    Raises:
        FileNotFoundError: If the .env file does not exist.
        ValueError: If the .env file is empty, cannot be read, or required variables are missing.
        Exception: If any other error occurs during the loading of the .env file.
    """
    def mask_string(s):
        """Masks all but the first three characters of a string."""
        if len(s) <= 3:
            return s
        return s[:3] + '*' * (len(s) - 3)

    try:
        env_credentials: dict[str, str | None] = dotenv_values(".env")
        if not env_credentials:
            raise ValueError(
                "Failed to load environment variables from .env file")

        if ("DSB_USERNAME" not in env_credentials or "DSB_PASSWORD" not in env_credentials):
            raise ValueError(
                "DSB_USERNAME and DSB_PASSWORD must be set in the .env file")

        # Prevent empty values
        for value in env_credentials.values():
            if not value:
                raise ValueError

        return env_credentials

    except FileNotFoundError:
        logger.warning(
            "The .env file does not exist, falling back to OS environment")

    except ValueError:
        logger.warning(
            "Failed to load variables from .env file, falling back to OS environment")

    # Fallback to load environment variables from OS environment
    dsb_username: str | None = getenv("DSB_USERNAME")
    dsb_password: str | None = getenv("DSB_PASSWORD")

    if not dsb_username or not dsb_password:
        logger.critical(
            "DSB_USERNAME and DSB_PASSWORD must be set in the .env file or the OS environment")
        raise ValueError(
            "DSB_USERNAME and DSB_PASSWORD must be set in the .env file or the OS environment")

    logger.info("OS environment Credentials:")
    logger.info("-----------------")
    logger.info("Username: %s", mask_string(dsb_username))
    logger.info("Password: %s", mask_string(dsb_password))

    return {
        "DSB_USERNAME": dsb_username,
        "DSB_PASSWORD": dsb_password
    }


def prepare_api_url(credentials: dict[str, str | None]) -> str:
    """
    Prepare the API URL for the "DaVinci Touch" section from the given credentials.

    Args:
        credentials (dict): Dictionary containing 'username' and 'password' for authentication.

    Returns:
        str: The base URL for the "DaVinci Touch" section if found.

    Raises:
        KeyError: If a required credential is missing.
        ValueError: If the "DaVinci Touch" section is not found.
        Exception: For other unforeseen errors.
    """

    logger.info("Sending API request")

    try:
        dsb = PyDSB(credentials["DSB_USERNAME"],  # type: ignore
                    credentials["DSB_PASSWORD"])  # type: ignore
        data = dsb.get_postings()

    except requests.ConnectionError as e:
        logger.critical("No Internet Connection: %s", e)
        raise

    for section in data:
        if section["title"] == "DaVinci Touch":
            base_url = section["url"]
            logger.debug("URL for DaVinci Touch: %s", base_url)
            return base_url

    # This line is reached if no section titled "DaVinci Touch" is found
    raise ValueError("DaVinci Touch section not found.")


def request_url_data(url: str) -> BeautifulSoup:
    """
    Send a GET request to the specified URL and return a BeautifulSoup object parsed from the
    HTML response.

    Args:
        url (str): The URL to send the request to.

    Returns:
        BeautifulSoup: A BeautifulSoup object of the parsed HTML document.

    Raises:
        requests.exceptions.RequestException: If the request fails for any reason, including
        network issues, invalid URLs, or HTTP errors.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raises HTTPError for bad responses
    except requests.exceptions.RequestException as e:
        logger.error("Failed to fetch data from %s: %s", url, e)
        raise

    html = response.content.decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    return soup


def get_plans(base_url: str) -> dict[str, str]:
    """
    Extract plans from the given base URL and organize them in a dictionary.

    Args:
        base_url (str): The base URL containing the plan information.

    Returns:
        dict: A dictionary mapping plan identifiers to their URLs.
            e.g. {'1_Montag': 'https://light.dsbcontrol.de/DSBlightWebsite/Data/{id}/V_DC_001.html'}

    Raises:
        ValueError: If the expected HTML structure is not found.
    """
    logger.info("Extracting Posts")
    soup = request_url_data(base_url)

    try:
        # Find all <a> tags within the <ul> element with class "day-index"
        links = soup.find(
            "ul", class_="day-index").find_all("a")  # type: ignore

        # Print a warning if no <a> tags are found
        if not links:
            logger.warning(
                "No <a> tags found with class 'day-index'")
            return {}

    except AttributeError as e:
        logger.error("Error parsing HTML structure: %s", e)
        raise ValueError("Expected HTML structure not found.") from e

    logger.debug("<a> links in <ul>, found by soup: %s", links)

    # Extract href attributes and link text
    href_links = [link.get("href") for link in links]
    text_list = [link.text for link in links]

    # change format from ["02.09.2024 Mittwoch", ...] to ["Montag_02-09-2024", ...]
    weekdays_with_date = [f"{day}_{date.replace('.', '-')}"
                          for date, day in (item.split() for item in text_list)]
    logger.info(weekdays_with_date)

    # Construct posts dictionary
    posts_dict = {}
    for href, weekday in zip(href_links, weekdays_with_date):
        if weekday:  # Only include entries with a valid weekday
            full_url = urljoin(base_url, href)
            posts_dict[f"{weekday}"] = full_url
            logger.debug("Added %s to posts_dict: %s", weekday, full_url)
    return posts_dict


def main_scraping(url: str, course: str) -> tuple[list[list[str]], bool]:
    """
    Scrape a given URL for specific table data related to a course.

    Args:
        url (str): The URL to scrape data from.
        course (str): The course identifier to search for in the table.

    Returns:
        tuple[list[list[str]], bool]: A tuple containing:
            - A list of lists containing the scraped table data for the course
            - A boolean indicating whether the course was found

    Raises:
        ValueError: If the table element is not found in the HTML.
        Exception: If any other error occurs during HTML processing.
    """

    soup = request_url_data(url)
    success = False
    total_replacements = []

    try:
        table = soup.find("table")
        if not table:
            raise ValueError("Table element not found in the HTML.")

        for row in table.find_all("tr"):  # type: ignore
            columns = row.find_all("td")
            if columns and columns[0].get_text().strip() == course:
                success = True
                logger.debug("%s found", course)
                replacement = [col.get_text().strip() for col in columns]
                total_replacements.append(replacement)

                next_row = row.find_next_sibling("tr")
                count = 1
                while next_row and "\xa0" in next_row.find("td").get_text():
                    logger.debug("New row found! %s", count)
                    replacement = [
                        col.get_text().strip() for col in next_row.find_all("td")
                    ]
                    total_replacements.append(replacement)
                    next_row = next_row.find_next_sibling("tr")
                    count += 1
    except Exception as e:
        logger.error("Error processing HTML: %s", e)
        raise
    logger.debug("Success Status: %s", success)
    return total_replacements, success


def run_main_scraping(posts_dict: dict[str, str],
                      course: str | None, print_output: bool) -> dict[str, list[list[str]]]:
    """
    Execute the main_scraping function for each URL in the given dictionary.

    Args:
        posts_dict (dict[str, str]): A dictionary mapping identifiers to URLs.
        course (str | None): The course identifier to search for in the tables.
        print_output (bool): Whether to print the scraped data to console.

    Returns:
        dict[str, list[list[str]]]: Dictionary mapping identifiers to the scraped data for each URL.

    Raises:
        ValueError: If the course argument is None.
    """
    if course is None:
        logger.error("Course argument must have a string value if provided")
        raise ValueError(
            "Course argument must have a string value if provided")

    scrape_dict = {}
    for key, url in posts_dict.items():
        try:
            scraped_data, success = main_scraping(url, course)
            scrape_dict[key] = scraped_data
            if success:
                logger.info("%s: found %s entries!", key, course)
            else:
                logger.warning("%s: class %s not found!", key, course)
        except Exception as e:  # pylint: disable=W0718
            logger.error("Failed to scrape %s: %s", url, e)
            scrape_dict[key] = []  # Assign an empty list in case of failure
    if print_output:
        logger.info(
            "%s",
            json.dumps(scrape_dict, indent=2, ensure_ascii=False)
            .encode("utf8")
            .decode("utf8"),
        )
    return scrape_dict

# TODO: also check json/formatted.json


def save_data_if_changed(new_data: dict, file_path: str) -> bool:
    """
    Compare new data with existing file content and save if different.
    """
    try:
        with open(file_path, 'r', encoding='utf8') as file:
            existing_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        existing_data = None

    if existing_data == new_data:
        logger.debug("No changes detected in scraped data. Aborting.")
        return False

    with open(file_path, "w", encoding="utf8") as file_json:
        json.dump(new_data, file_json, ensure_ascii=False)
    logger.info("Scraped data saved to %s", file_path)
    return True


def main(args: argparse.Namespace) -> bool:
    """
    Main function that orchestrates the scraping process.
    """
    # Setup logger
    setup_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    logger.info("Script started successfully")

    # Load environment credentials
    env_credentials: dict[str, str | None] = load_env_credentials()

    # Prepare API URL
    base_url: str = prepare_api_url(env_credentials)

    # Get plans
    posts_dict: dict[str, str] = get_plans(base_url)

    # Scrape data
    class_dict: dict[str, list[list[str]]] = run_main_scraping(
        posts_dict, args.course, args.print_output)

    # Save data if changed
    return save_data_if_changed(class_dict, args.raw_file)


if __name__ == "__main__":
    # DEFAULT VALUES
    default_args = argparse.Namespace(verbose=False, course='MSS12',
                                      print_output=False, raw_file='json/scraped.json')
    main(default_args)
