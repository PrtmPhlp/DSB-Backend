import requests
from bs4 import BeautifulSoup
import json

# URL der Webseite
url = 'https://www.goerres-koblenz.de/kollegium/'

# HTTP-Anfrage an die Webseite senden
response = requests.get(url)
response.raise_for_status()  # Überprüfen, ob die Anfrage erfolgreich war

# Inhalt der Webseite parsen
soup = BeautifulSoup(response.text, 'html.parser')

# Dictionary zur Speicherung der Lehrerdaten
lehrer_dict = {}

# Tabelle mit den Lehrerdaten finden
table = soup.find('table')

# Zeilen der Tabelle durchlaufen (erste Zeile enthält die Header)
for row in table.find_all('tr')[1:]:
    cells = row.find_all('td')
    if len(cells) >= 4:
        kuerzel = cells[0].get_text(strip=True)
        nachname = cells[1].get_text(strip=True)
        vorname = cells[2].get_text(strip=True)
        faecher = cells[3].get_text(strip=True)
        name = vorname + ' ' + nachname
        lehrer_dict[kuerzel] = {
            'Name': name,
            'Nachname': nachname,
            'Vorname': vorname,
            'Fächer': faecher
        }

# Dictionary als JSON in Datei speichern
with open('json/lehrer.json', 'w', encoding='utf-8') as json_file:
    json.dump(lehrer_dict, json_file, ensure_ascii=False, indent=4)

print('Lehrerdaten wurden erfolgreich in "lehrer.json" gespeichert.')
