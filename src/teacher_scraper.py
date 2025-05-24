import json
from pathlib import Path
from typing import Any, Dict

import requests
from bs4 import BeautifulSoup, Tag

from logger_setup import LoggerSetup

# ---------------------------------------------------------------------------
# 1) Logger Setup
# ---------------------------------------------------------------------------
logger = LoggerSetup.setup_logger("TeacherScraper")

class TeacherScraper:
    """
    Scrape teacher data from a specified URL and save it to a JSON file.
    """
    def __init__(self, url: str, output_path: str, timeout: int = 10):
        self.url = url
        self.output_path = Path(output_path)
        self.timeout = timeout
        self.lehrer_dict: Dict[str, Any] = {}

    def fetch_page(self) -> str:
        """Fetch the webpage content."""
        response = requests.get(self.url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def parse_teacher_data(self, html: str) -> None:
        """Parse teacher data from HTML content."""
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')

        if not table or not isinstance(table, Tag):
            raise ValueError("Keine Tabelle mit Lehrerdaten gefunden")

        rows = table.find_all('tr')
        if len(rows) > 1:
            for row in rows[1:]:
                if isinstance(row, Tag):
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        self._process_row(cells)

    def _process_row(self, cells) -> None:
        """Process a single row of teacher data."""
        kuerzel = cells[0].get_text(strip=True)
        nachname = cells[1].get_text(strip=True)
        vorname = cells[2].get_text(strip=True)
        faecher = cells[3].get_text(strip=True)

        self.lehrer_dict[kuerzel] = {
            'Name': f"{vorname} {nachname}",
            'Vorname': vorname,
            'Nachname': nachname,
            'Fächer': faecher
        }

    def save_to_json(self) -> None:
        """Save teacher data to JSON file."""
        self.output_path.parent.mkdir(exist_ok=True)
        with open(self.output_path, 'w', encoding='utf-8') as json_file:
            json.dump(self.lehrer_dict, json_file, ensure_ascii=False, indent=4)

    def run(self) -> None:
        """Execute the complete scraping process."""
        try:
            html = self.fetch_page()
            self.parse_teacher_data(html)
            self.save_to_json()
            logger.info('Teacher data saved in "%s"', self.output_path)
        except Exception as e:
            logger.error('Error scraping teacher data: %s', e)


if __name__ == '__main__':
    URL = 'https://www.goerres-koblenz.de/kollegium/'
    OUTPUT_FILE = 'schema/lehrer.json'

    scraper = TeacherScraper(URL, OUTPUT_FILE)
    scraper.run()
