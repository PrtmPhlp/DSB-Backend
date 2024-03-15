#!/usr/bin/env python3
# ------------------------------------------------
# ! Imports

# ? Logging and Argsparse
from urllib.parse import urljoin
import coloredlogs
import logging
import argparse
import yaml

# ? Scraping
import requests
from bs4 import BeautifulSoup
from pydsb import PyDSB
import json

# ------------------------------------------------
# ? Arguments
parser = argparse.ArgumentParser()
# parser.add_argument("day", type=int, nargs='?', help="Tag für den Vertretungsplan, z.B.: 4")
parser.add_argument('verbose', type=int, nargs='?', default='1')
args = parser.parse_args()

# ? Logging
logger = logging.getLogger(__name__)

# Determine logging level based on args.verbose
if args.verbose == 0:
    logging_level = logging.CRITICAL
elif args.verbose == 2:
    logging_level = logging.DEBUG
    # prevent requests (urllib3) logging:
    logging.getLogger("urllib3").setLevel(logging.WARNING)
else:
    logging_level = logging.INFO

logger.setLevel(logging_level)
coloredlogs.install(fmt="%(asctime)s - %(levelname)s - \033[94m%(message)s\033[0m",
                    datefmt="%H:%M:%S", level=logging_level)

# ? load dsb credentials from secrets
with open('./secrets/secrets.yaml') as file:
    credentials = yaml.safe_load(file)
# ------------------------------------------------


def prepare_api_url(credentials: dict) -> str:
    """
    Prepares the API URL for the "DaVinci Touch" section from the given credentials.

    :param credentials: Dictionary containing 'username' and 'password' for auth.
    :return: The base URL for "DaVinci Touch" section if found.
    :raises KeyError: If a required credential is missing.
    :raises Exception: For other unforeseen errors.
    :raises ValueError: If the "DaVinci Touch" section is not found.
    """
    logger.info("Sending API request")
    try:
        dsb = PyDSB(credentials['dsb']['username'],
                    credentials['dsb']['password'])
        data = dsb.get_postings()
    except requests.ConnectionError as e:
        print("Exception occurred: ", e)
        logger.critical(
            "No Internet Connection")
    # except Exception as e:
    #     logger.error("An unexpected error occurred: %s", e)
        raise

    for section in data:
        if section["title"] == "DaVinci Touch":
            base_url = section["url"]
            logger.debug("URL for DaVinci Touch: %s", base_url)
            return base_url

    # This line is reached if no section titled "DaVinci Touch" is found
    raise ValueError("DaVinci Touch section not found.")


def request_url(url: str) -> BeautifulSoup:
    """
    Sends a GET request to the specified URL and returns a BeautifulSoup object parsed from the HTML response.

    :param url: The URL to send the request to.
    :return: A BeautifulSoup object of the parsed HTML document.
    :raises requests.exceptions.RequestException: If the request fails for any reason, including network issues,
           invalid URLs, or HTTP errors.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises HTTPError for bad responses
    except requests.exceptions.RequestException as e:
        # Uncomment the logger statement if logging is desired.
        # logger.error(f"Failed to fetch data from {url}: {e}")
        raise

    html = response.content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    return soup


def get_plans(base_url: str) -> dict[str, str]:
    """
    Extracts plans from the given base URL and organizes them in a dictionary.

    :param base_url: The base URL containing the plan information.
    :return: A dictionary mapping plan identifiers to their URLs.
    """
    logger.info("Extracting Posts")
    soup = request_url(base_url)

    try:
        links = soup.find(
            'ul', class_='day-index').find_all('a')  # type: ignore

    except AttributeError as e:
        logger.error(f"Error parsing HTML structure: {e}")
        raise ValueError("Expected HTML structure not found.")

    logger.debug("<a> links in <ul>, found by soup: %s", links)

    # Extract href attributes and link text
    href_links = [link.get('href') for link in links]
    text_list = [link.text for link in links]

    weekdays = ["Montag", "Dienstag", "Mittwoch",
                "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    # Extract weekdays from text_list
    extracted_weekdays = [next(
        (weekday for weekday in weekdays if weekday in text), None) for text in text_list]

    # Construct posts dictionary
    posts_dict = {}
    for i, (href, weekday) in enumerate(zip(href_links, extracted_weekdays)):
        if weekday:  # Only include entries with a valid weekday
            full_url = urljoin(base_url, href)
            posts_dict[f"{i+1}_{weekday}"] = full_url
            logger.debug(f"Added {weekday} to posts_dict: {full_url}")

    return posts_dict


def main_scraping(url: str) -> tuple[list[list[str]], bool]:
    """
    Scrapes a given URL for specific table data related to 'MSS11'.

    :param url: The URL to scrape data from.
    :return: A list of lists containing the scraped table data.
    """
    soup = request_url(url)
    success = False

    total_replacements = []

    try:
        table = soup.find('table')
        if not table:
            raise ValueError("Table element not found in the HTML.")

        for row in table.find_all('tr'):  # type: ignore
            columns = row.find_all('td')
            if columns and columns[0].get_text().strip() == 'MSS11':
                success = True
                logger.debug("MSS11 found")
                replacement = [col.get_text().strip() for col in columns]
                total_replacements.append(replacement)

                next_row = row.find_next_sibling('tr')
                while next_row and "\xa0" in next_row.find("td").get_text():
                    logger.debug("New row found!")
                    replacement = [col.get_text().strip()
                                   for col in next_row.find_all('td')]
                    total_replacements.append(replacement)
                    next_row = next_row.find_next_sibling('tr')
    except Exception as e:
        logger.error(f"Error processing HTML: {e}")
        raise
    logger.debug(f"Success Status: {success}")
    return total_replacements, success


def run_main_scraping(posts_dict: dict[str, str]) -> dict[str, list[list[str]]]:
    """
    Executes the main_scraping function for each URL in the given dictionary and updates the dictionary with the results.

    :param posts_dict: A dictionary mapping identifiers to URLs.
    :return: A dictionary mapping identifiers to the results of the scraping process.
    """
    scrape_dict = {}
    for key, url in posts_dict.items():
        try:
            scraped_data, success = main_scraping(url)
            scrape_dict[key] = scraped_data
            if success:
                logger.info(f"{key}: scraped successfully!")
            else:
                logger.warning(f"{key}: class not found!")
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            scrape_dict[key] = []  # Assign an empty list in case of failure

    return scrape_dict


def main():
    baseUrl = prepare_api_url(credentials)
    posts_dict = get_plans(baseUrl)

    scrape_dict = run_main_scraping(posts_dict)
    logger.debug(
        f"{json.dumps(scrape_dict, indent=2, ensure_ascii=False).encode("utf8").decode("utf8")}")

    with open("file.json", "w", encoding="utf8") as file:
        json.dump(scrape_dict, file, ensure_ascii=False)
        logger.info("saved to file!")


if __name__ == "__main__":
    main()
