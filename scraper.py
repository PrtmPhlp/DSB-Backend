#!/usr/bin/env python3
# ------------------------------------------------
# ! Imports

# ? Logging and Argsparse
import coloredlogs
import logging
import argparse

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
# ------------------------------------------------


def prep_API_URL():
    logger.info("Sending API request")

    dsb = PyDSB("274583", "johann")
    data = dsb.get_postings()

    for section in data:
        if section["title"] == "DaVinci Touch":
            baseUrl = section["url"]
    logger.debug("URL für DaVinci Touch: %s", baseUrl)
    return baseUrl


baseUrl = prep_API_URL()


response = requests.get(baseUrl)
html = response.content.decode('utf-8')
soup = BeautifulSoup(html, 'html.parser')

links = soup.find('ul', class_='day-index').find_all('a')

# Extract href attributes from the 'a' tags
href_links = [link.get('href') for link in links]
baseUrl = baseUrl.split("index.html")[0]
for link in href_links:
    ver = baseUrl + link
    print(ver)

logger.info(href_links)
