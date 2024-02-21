#!/usr/bin/env python3
# ------------------------------------------------
# ! Imports

# ? Logging and Argsparse
import random
import coloredlogs
import logging
import argparse
import yaml

# ? Scraping related
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from pydsb import PyDSB
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
else:
    logging_level = logging.INFO

logger.setLevel(logging_level)
coloredlogs.install(fmt="%(asctime)s - %(levelname)s - \033[94m%(message)s\033[0m",
                    datefmt="%H:%M:%S", level=logging_level)

# ? load dsb credentials from secrets
with open('./secrets/secrets.yaml') as file:
    credentials = yaml.safe_load(file)
# ------------------------------------------------


def prep_API_URL():
    logger.info("Sending API request")

    dsb = PyDSB(credentials['dsb']['username'], credentials['dsb']['password'])
    data = dsb.get_postings()

    for section in data:
        if section["title"] == "DaVinci Touch":
            baseUrl = section["url"]
    logger.debug("URL für DaVinci Touch: %s", baseUrl)
    return baseUrl


# ? Get all representation plans from baseUrl and save in "posts_dict"
def get_plans(baseUrl):
    logger.info("Extracting Posts")

    response = requests.get(baseUrl)
    html = response.content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    links = soup.find('ul', class_='day-index').find_all('a')
    logger.debug("<a> links in <ul>, found by soup: %s", links)

    href_links = [link.get('href') for link in links]
    logger.debug("extracted following href links: %s", href_links)

    text_list = [link.text for link in links]

    # remove index.html and everything after it
    baseUrl = baseUrl.split("index.html")[0]

    weekdays = ["Montag", "Dienstag", "Mittwoch",
                "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    # remove everything from text_list except the weekday
    extracted_weekdays = []
    for text in text_list:
        for weekday in weekdays:
            if weekday in text:
                extracted_weekdays.append(weekday)
                break  # Stoppe die Schleife, sobald ein Wochentag gefunden wurde

    posts_dict = {}
    for i in range(len(href_links)):
        logger.debug(f"Text list at {i+1} run: {text_list[i]}")
        logger.debug(f"href link at {i+1} run: {href_links[i]}")
        posts_dict[extracted_weekdays[i]] = baseUrl + href_links[i]
        logger.debug(f"posts_dict at {i+1} run: {posts_dict}")
    return posts_dict


baseUrl = prep_API_URL()
posts_dict = get_plans(baseUrl)
logger.info(posts_dict)