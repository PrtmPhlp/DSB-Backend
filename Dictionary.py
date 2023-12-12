import json

import requests
from bs4 import BeautifulSoup

url = "https://www.goerres-koblenz.de/kollegium/"
# GET-Anfrage an die Website senden
response = requests.get(url)

# Das Encoding der Response-Inhalte manuell auf UTF-8 setzen
response.encoding = "utf-8"

# BeautifulSoup-Objekt erstellen
soup = BeautifulSoup(response.content, "html.parser")

# Tabelle finden
table = soup.find("table")

# Alle Zeilen der Tabelle finden
rows = table.find_all("tr")

# Ein leeres Python-Dictionary erstellen
my_dict = {}

# Die ersten vier td-Tags jeder Zeile durchlaufen und zum Dictionary hinzufügen
for row in rows:
    cols = row.find_all("td")
    if cols:
        key1 = cols[0].text.strip()
        key2 = cols[1].text.strip() + " " + cols[2].text.strip()
        # Konvertierung der Unicode-Zeichen in Umlaute
        value = cols[3].text.strip()
        # Konvertierung der Unicode-Zeichen in Umlaute
        # Wenn der erste Key bereits im Dictionary existiert, füge den Value als Listenelement hinzu
        if key1 in my_dict:
            my_dict[key1][key2] = value
        # Ansonsten füge den ersten Key und eine neue Liste mit dem zweiten Key-Value-Paar hinzu
        else:
            my_dict[key1] = {key2: value}

# Das Python-Dictionary in JSON konvertieren und in die Datei "output2.json" schreiben
with open("lehrer.json", "w", encoding="utf-8") as f:
    json.dump(my_dict, f, ensure_ascii=False)

"""
import json

# Das JSON-Dictionary aus der Datei "lehrer.json" laden
with open('lehrer.json', 'r', encoding='utf-8') as f:
    my_dict = json.load(f)

output = my_dict['VARIABLE']
# Erster Value:
print(list(output.keys())[0])
# Zweiter Value
print(output[list(output.keys())[0]])
"""
