#!/usr/bin/env python3
# ------------------------------------------------
# ! Imports

# ? Logging and Argsparse
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


def prep_API_URL() -> str:
    logger.info("Sending API request")
    try:
        # Your code that makes the request
        dsb = PyDSB(credentials['dsb']['username'],
                    credentials['dsb']['password'])
        data = dsb.get_postings()
        # Process the response
    except Exception as e:
        print("An error occurred:", e)

    for section in data:
        if section["title"] == "DaVinci Touch":
            baseUrl = section["url"]
    logger.debug("URL für DaVinci Touch: %s", baseUrl)
    return baseUrl


# ? Get all representation plans from baseUrl and save in "posts_dict"
def get_plans(baseUrl: str) -> dict[str, str]:
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
    logger.info(f"Found following days: {extracted_weekdays}")
    posts_dict = {}
    for i in range(len(href_links)):
        logger.debug(f"Text list at {i+1} run: {text_list[i]}")
        logger.debug(f"href link at {i+1} run: {href_links[i]}")
        posts_dict[str(i+1) + "_" + extracted_weekdays[i]
                   ] = baseUrl + href_links[i]
        logger.debug(f"posts_dict at {i+1} run: {posts_dict}")

    return posts_dict


def main_scraping(url):

    gesamte_vertretungen = []
    response = requests.get(url)
    html = response.content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    # Durch alle <tr>-Elemente der Tabelle iterieren
    for row in table.find_all('tr'):
        columns = row.find_all('td')

        # Überprüfen, ob das erste <td>-Element "MSS11" enthält
        if columns and columns[0].get_text().strip() == 'MSS11':
            logger.debug("MSS11 gefunden")
            vertretung = []

            # Den Inhalt des aktuellen <tr>-Elements speichern
            for col in columns:
                text = col.get_text().strip()
                vertretung.append(text)
            gesamte_vertretungen.append(vertretung)

            # Das nächste <tr>-Element durchlaufen
            next_row = row.find_next_sibling('tr')
            while next_row:
                first_td = next_row.find("td")
                if first_td and "\xa0" in str(first_td):
                    logger.debug("Neue Zeile gefunden!")
                    vertretung = []

                    for col in next_row.find_all('td'):
                        text = col.get_text().strip()
                        vertretung.append(text)
                    gesamte_vertretungen.append(vertretung)

                    # Zum nächsten <tr>-Element übergehen
                    next_row = next_row.find_next_sibling('tr')
                else:
                    logger.debug("Keine neue Zeile mit \xa0 gefunden")
                    break
    return gesamte_vertretungen


def run_main_scraping(posts_dict):
    scrape_dict = posts_dict.copy()
    for key, val in scrape_dict.items():
        # Main Scraping durchführen und Ergebnis in String konvertieren
        ges = main_scraping(val)
        scrape_dict[key] = str(ges)
        logger.debug(ges)
        # Eval verwenden, um den Wert in eine Liste umzuwandeln
        converted_value = eval(scrape_dict[key])
        scrape_dict[key] = converted_value
        logger.info(f"{key}: scraped!")
    return scrape_dict


def main():
    baseUrl = prep_API_URL()
    posts_dict = get_plans(baseUrl)

    scrape_dict = run_main_scraping(posts_dict)
    print(f"{scrape_dict=}")

    with open("file.json", "w") as file:
        json.dump(scrape_dict, file)


if __name__ == "__main__":
    main()