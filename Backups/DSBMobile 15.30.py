#!/opt/homebrew/bin/python3.10

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title DSBMobile
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 🧭
# @raycast.packageName Vertretungsplan

# Documentation:
# @raycast.description Plays Pop Sender in Apple Music
# @raycast.author PrtmPhlp
# @raycast.authorURL https://github.com/PrtmPhlp

from pydsb import PyDSB
import requests
import json
from bs4 import BeautifulSoup
from termcolor import colored
import re
from datetime import datetime
import argparse
import subprocess

# ? Arguments for CLI
parser = argparse.ArgumentParser(description='Vertretungsplan Skript mithilfe API')
parser.add_argument("day",type=int, nargs='?', help="Tag für den Vertretungsplan, z.B.: 4")
parser.add_argument("verbose",type=int, nargs='?', help="De / aktiviert den stillen Modus")
args = parser.parse_args()

if args.day is None:
    day = 1
else:
    day = args.day

if args.verbose is None or args.verbose == 0:
    global verbose
    verbose = 0
else:
    verbose = 1
    import os
    # umleiten von stdout auf /dev/null
    devnull = open(os.devnull, 'w')
    old_stdout = os.dup(1)
    os.dup2(devnull.fileno(), 1)


# ? Internet Check. If not then exit
def prep_check_internet():
    try:
        requests.get('http://www.google.com', timeout=3)
        return True
    except requests.exceptions.ConnectionError:
        return False

    if not check_internet_connection():
        print(colored('Error: No internet connection', 'red', attrs=['bold', 'blink']))
        exit()


# ? Use PyDSB and gather URLs
def prep_API_URL():
    print(colored("Info: Sending API request", 'yellow', attrs=['bold']))

    dsb = PyDSB("274583", "johann")
    global data
    data = dsb.get_postings()


# ? Gather's Content from every possible URL and see's if the day is in the future
def act_future_list_check():
    print(colored("Info: Creating URL", 'yellow', attrs=['bold']))
    # Iterieren über die Liste, um den richtigen Eintrag zu finden
    for posting in data:
        if posting['title'] == 'DaVinci Touch':
            # Ersetzt das Datum in der URL durch den Platzhalter und hängt ".html" an
            global new_posting
            new_posting = posting['url'].split("/in")[0] + "/V_DC_00" + str(day) + ".html"
            auto_pos = posting['url'].split("/in")[0] + "/V_DC_00"
            # Loop durchläuft die Kombinationen von URLs, bis eine nicht antwortet
            count = 1
            word_list = []
            while True:
                try:
                    r = requests.get(auto_pos + str(count) + str(".html"), timeout=5)
                    r.raise_for_status()  # Überprüfen auf HTTP-Statuscode
                    print(f"{auto_pos}{count}.html ist erreichbar.")

                    # Erstellen Sie ein BeautifulSoup-Objekt und suchen Sie nach dem h1-Element
                    soup = BeautifulSoup(r.content, 'html.parser')
                    h1_element = soup.find('h1', class_='list-table-caption')

                    # Wenn das h1-Element gefunden wird, extrahieren Sie das erste Wort des Textinhalts und fügen Sie es zur Liste hinzu
                    if h1_element is not None:
                        h1_text = h1_element.text.strip()
                        first_word = h1_text.split()[0]
                        words = h1_text.split()
                        result = ' '.join(words[1:])

                        dt = datetime.now().strftime('%d.%m.%Y')
                        today = datetime.strptime(dt, '%d.%m.%Y')
                        past = datetime.strptime(result, "%d.%m.%Y")
                        if past < today:
                            print(colored(h1_text+": Ist in der Vergangenheit", 'red', attrs=['bold']))

                        else:
                            print(colored(h1_text+": Ist in der Zukunft", 'green', attrs=['bold']))
                            word_list.append(first_word)

                    else:
                        print("Kein h1-Element mit der Klasse 'list-table-caption' gefunden.")

                    count += 1
                except requests.exceptions.RequestException as e:
                    print(f"{auto_pos}{count}.html ist nicht erreichbar.")
                    break

            print(word_list)  # Gibt die Liste der ersten Wörter der h1-Elemente aus

#? Suche nach Zeile mit 10a in der ersten Spalte
def act_main_vertretung():
    response = requests.get(new_posting)
    html = response.content.decode('utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    table = soup.find('table')

    stop_at_empty_row = False
    global ergebnisse_ver1
    ergebnisse_ver1 = []

    for row in table.find_all('tr'):
        columns = row.find_all('td')
        if columns and columns[0].get_text().strip() == '10a':
            global vertretung_1
            vertretung_1 = [col.get_text().strip() for col in columns if col.get_text().strip()]
            print(colored(vertretung_1, 'green', attrs=['bold']))
            next_row = row.find_next_sibling('tr')
            if next_row:
                zeile = str(next_row).replace('\n', '')
                while zeile and not stop_at_empty_row:
                    if re.search(r'<td>[a-zA-Z]?</td>', zeile):
                        empty_col_index = None
                        for i, col in enumerate(next_row.find_all('td')):
                            if '\xa0' in zeile:
                                empty_col_index = i
                                break

                        if empty_col_index is not None and empty_col_index < len(next_row.find_all('td')) - 1:
                            vertretung_2 = [col.get_text().strip() for col in next_row.find_all('td')[empty_col_index + 1:] if col.get_text().strip()]
                            
                            ergebnisse_ver1.append("E")
                            ergebnisse_ver1.append(vertretung_2)
                            print(colored(vertretung_2, 'green', attrs=['bold']))
                            next_row = next_row.find_next_sibling('tr')
                            zeile = str(next_row).replace('\n', '')
                        else:
                            stop_at_empty_row = True

                    else:
                        stop_at_empty_row = True
            else:
                stop_at_empty_row = True

        elif columns and columns[0].get_text().strip() == '':
            continue
        elif columns and '\xa0' in columns[0].get_text().strip():
            empty_col_index = None
            for i, col in enumerate(columns):
                if '\xa0' in col.get_text().strip():
                    empty_col_index = i
                    break
            if empty_col_index is not None and empty_col_index < len(columns) - 1:
                vertretung_3 = [col.get_text().strip() for col in columns[empty_col_index + 1:] if col.get_text().strip()]
                print(colored("hey"+vertretung_3, 'green', attrs=['bold']))
            else:
                stop_at_empty_row = True

def aft_combiner():
    if 'vertretung_1' in globals():
        #print("Variable x wurde definiert.")
        global kombiniert
        kombiniert = vertretung_1.copy()
        kombiniert.extend([item for sublist in ergebnisse_ver1 for item in sublist])

        # Serialize the variable into a JSON string
        global json_string
        json_string = json.dumps(kombiniert)
        print("aft_combiner: " + json_string)
        # Open a file and write the JSON string to it
        with open('output.json', 'w') as f:
            f.write(json_string)

# Define the variable to be written to file
def speicher_versuch(file_path, json_string):
    if verbose == 1:
        os.dup2(old_stdout, 1)
        devnull.close()
        
    try:
        with open(file_path, 'w') as f:
            f.write(json_string)
        if verbose != 1: print(colored("Info: Output erfolgreich in vertretung.json gespeichert.", 'yellow', attrs=['bold']))
    except NameError:
        for row in table.find_all('tr'):
            columns = row.find_all('td')
            if columns and columns[0].get_text().strip() == '10b':
                ex_vertretung=([col.get_text().strip() for col in columns if col.get_text().strip()])
                error_msg_info="Fehler: Keine Vertretung für 10a gefunden. 10b verfügbar"
                print(colored(error_msg_info, 'red'))
        try:
            ex_vertretung
        except NameError:
            error_msg="Fehler: Keine Vertretung für 10a & 10b gefunden"
            print(colored(error_msg, 'red', attrs=['bold']))
            exit()



def andere_klassen():
    for klasse in ['5a', '5b', '5c', '6a', '6b', '6c', '7a', '7b', '7c', '8a', '8b', '8c', '9a', '9b', '9c', '10a', '10b']:
        print(f"Info: Checking for Vertretung in Klasse {klasse}")
        
        found = False
        for row in table.find_all('tr'):
            columns = row.find_all('td')
            if columns and columns[0].get_text().strip() == klasse:
                vertretung = [col.get_text().strip() for col in columns if col.get_text().strip()]
                print(colored(vertretung, 'green', attrs=['bold']))
                found = True
                
        if not found:
            error_msg = f"Fehler: Keine Vertretungsinformationen gefunden für Klasse {klasse}."
            print(colored(error_msg, 'red', attrs=['bold']))

#! Function menu
prep_check_internet()
prep_API_URL()
act_future_list_check()
act_main_vertretung()
aft_combiner()
file_path = 'vertretung.json'
speicher_versuch(file_path, json_string)

try:
    print(kombiniert)
except NameError:
    print("ne")