from bs4 import BeautifulSoup
import requests
# HTML-Daten
# html_data = """
# <dein_html_code>
# </table>
# """

url = 'https://light.dsbcontrol.de/DSBlightWebsite/Data/86d013b9-c2de-4644-bdf6-43a413038ad1/63ef68c4-d2cd-4d50-9544-f1c237e8ed7e/V_DC_001.html'

response = requests.get(url)
html = response.content.decode('utf-8')
# BeautifulSoup-Objekt erstellen
soup = BeautifulSoup(html, 'html.parser')

# Das <table>-Tag finden
table = soup.find('table')

# Liste, um die Inhalte der relevanten <tr>-Elemente zu speichern
relevant_rows = []

# Flag, um zu markieren, dass "MSS11" gefunden wurde
found_mss11 = False

# Durch alle <tr>-Elemente der Tabelle iterieren
for tr in table.find_all('tr'):
    # Das erste <td>-Element des aktuellen <tr>-Elements finden
    first_td = tr.find('td')
    if first_td:
        # Überprüfen, ob der Inhalt "MSS11" ist
        if first_td.text.strip() == "MSS11":
            print("MSS11 gefunden")
            found_mss11 = True

        # Nach dem Finden von "MSS11" alle folgenden <tr> mit <td> = '\xa0' speichern
        if found_mss11:
            if first_td.text.strip() == "\xa0" or first_td.find(text='\xa0'):
                relevant_rows.append(tr)

# Die Inhalte der gefundenen <tr>-Elemente ausgeben (optional)
for row in relevant_rows:
    print(row)
