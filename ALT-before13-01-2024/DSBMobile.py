#!/opt/homebrew/bin/python3.10

import argparse
import json
import os
import re
import subprocess
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from pydsb import PyDSB
from termcolor import colored


# CLI-Argumente
def parse_args():
    parser = argparse.ArgumentParser(description="Vertretungsplan Skript mithilfe API")
    parser.add_argument(
        "day", type=int, nargs="?", help="Tag für den Vertretungsplan, z.B.: 4"
    )
    parser.add_argument(
        "verbose", type=int, nargs="?", help="De-/aktiviert den stillen Modus"
    )
    return parser.parse_args()


# Internetverbindung überprüfen
def check_internet_connection():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except requests.exceptions.ConnectionError:
        return False


# Vorbereitung: Internetverbindung überprüfen
def prep_check_internet():
    if not check_internet_connection():
        print(colored("Error: No internet connection", "red", attrs=["bold", "blink"]))
        exit()


# Vorbereitung: API-Anfrage senden und URLs abrufen
def prep_API_URL():
    print(colored("Info: Sending API request", "yellow", attrs=["bold"]))
    dsb = PyDSB("274583", "johann")
    global data
    data = dsb.get_postings()


# Überprüfen, ob der Tag in der Zukunft liegt
def act_future_list_check():
    print(colored("Info: Creating URL", "yellow", attrs=["bold"]))
    # Iterieren über die Liste, um den richtigen Eintrag zu finden
    for posting in data:
        if posting["title"] == "DaVinci Touch":
            # Ersetzt das Datum aus URL durch Platzhalter und ".html"
            global new_posting
            new_posting = (
                posting["url"].split("/in")[0] + "/V_DC_00" + str(day) + ".html"
            )
            auto_pos = posting["url"].split("/in")[0] + "/V_DC_00"
            # Loop durchläuft Kombinationen von URLs, bis eine nicht antwortet
            count = 1
            word_list = []
            while True:
                try:
                    r = requests.get(auto_pos + str(count) + str(".html"), timeout=5)
                    r.raise_for_status()  # Überprüfen auf HTTP-Statuscode
                    # BeautifulSoup-Objekt und suchen nach dem h1-Element
                    soup = BeautifulSoup(r.content, "html.parser")
                    h1_element = soup.find("h1", class_="list-table-caption")

                    # Wenn h1-Element gefunden, erstes Wort zur Liste
                    if h1_element is not None:
                        h1_text = h1_element.text.strip()
                        first_word = h1_text.split()[0]
                        words = h1_text.split()
                        j = " ".join(words[1:])

                        dt = datetime.now().strftime("%d.%m.%Y")
                        print(dt)
                        today = datetime.strptime(dt, "%d.%m.%Y")
                        print(today)
                        past = datetime.strptime(result, "%d.%m.%Y")
                        print(past)
                        if past < today:
                            print(
                                colored(
                                    h1_text + ": Ist in der Vergangenheit",
                                    "red",
                                    attrs=["bold"],
                                )
                            )

                        else:
                            print(
                                colored(
                                    h1_text + ": Ist in der Zukunft",
                                    "green",
                                    attrs=["bold"],
                                )
                            )
                            word_list.append(first_word)
                        print(f"{auto_pos}{count}.html ist erreichbar.")
                    else:
                        print(
                            "Kein h1-Element mit der Klasse 'list-table-caption' gefunden."
                        )

                    count += 1
                except requests.exceptions.RequestException:
                    print(
                        f"{auto_pos}{count}.html ist",
                        colored("nicht", "red", attrs=["bold"]),
                        "erreichbar.",
                    )
                    break

            print(word_list)  # Gibt die Liste der ersten Wörter der h1-Elemente aus


def write_to_json_file(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"Error writing to file: {e}")

# ? Suche nach Zeile mit MSS11 in der ersten Spalte
def act_main_vertretung():
    # Fetch and parse HTML content from new_posting URL
    response = requests.get(new_posting)
    html_content = response.content.decode("utf-8")
    parsed_html = BeautifulSoup(html_content, "html.parser")

    global table
    table = parsed_html.find("table")

    global results_list
    results_list = []

    for row in table.find_all("tr"):
        cells = row.find_all("td")

        # Process rows with "MSS11" in the first cell
        if cells and cells[0].get_text().strip() == "MSS11":
            global first_row_data
            first_row_data = [cell.get_text().strip() for cell in cells if cell.get_text().strip()]
            print(colored(first_row_data, "green", attrs=["bold"]))

            # Process subsequent rows based on specific conditions
            process_subsequent_rows(row)  # Corrected line

        # Skip empty rows
        elif cells and cells[0].get_text().strip() == "":
            continue
        # Handle rows with specific character in the first cell
        elif cells and "\xa0" in cells[0].get_text().strip():
            process_special_rows(cells)



def process_subsequent_rows(start_row):
    next_row = start_row.find_next_sibling("tr")
    row_data = "<tr>"

    while next_row:
        row_html = str(next_row).replace("\n", "")
        if re.search(r"<td>[a-zA-Z]?</td>", row_html):
            empty_col_index = find_empty_column_index(row_html, next_row)

            if empty_col_index is not None and empty_col_index < len(next_row.find_all("td")) - 1:
                subsequent_row_data = [cell.get_text().strip() for cell in next_row.find_all("td")[empty_col_index + 1:] if cell.get_text().strip()]
                results_list.extend(["Zeile", subsequent_row_data])
                print(colored(subsequent_row_data, "green", attrs=["bold"]))
                next_row = next_row.find_next_sibling("tr")
            else:
                break
        else:
            break
        
    write_to_json_file('vertretung.json', results_list)



def find_empty_column_index(row_html, row):
    for index, cell in enumerate(row.find_all("td")):
        if "\xa0" in row_html:
            return index
    return None


def process_special_rows(cells):
    empty_col_index = find_empty_column_index("", cells)
    if empty_col_index is not None and empty_col_index < len(cells) - 1:
        special_row_data = [cell.get_text().strip() for cell in cells[empty_col_index + 1:] if cell.get_text().strip()]
        print(colored("hey" + str(special_row_data), "green", attrs=["bold"]))



# def aft_combiner():
#     # print(vertretung_1)
#     if "vertretung_1" in globals():
#         # print("Variable x wurde definiert.")
#         global kombiniert
#         kombiniert = vertretung_1.copy()
#         kombiniert.extend([item for sublist in ergebnisse_ver1 for item in sublist])

#         # Serialize the variable into a JSON string
#         global json_string
#         try:
#             json_string = json.dumps(kombiniert)
#             print(json_string)
#         #    print("aft_combiner: " + json_string)
#         except NameError:
#             print(colored("Keine Vertretungen verfügbar", "yellow", attrs=["bold"]))


# # Define the variable to be written to file
# def speicher_versuch(file_path, json_string):
#     if verbose == 1:
#         os.dup2(old_stdout, 1)
#         devnull.close()

#     try:
#         with open(file_path, "w") as f:
#             f.write(json_string)
#         if verbose != 1:
#             print(
#                 colored(
#                     "Info: Output erfolgreich in vertretung.json gespeichert.",
#                     "yellow",
#                     attrs=["bold"],
#                 )
#             )
#     except NameError:
#         for row in table.find_all("tr"):
#             columns = row.find_all("td")
#             if columns and columns[0].get_text().strip() == "MSS12":
#                 ex_vertretung = [
#                     col.get_text().strip() for col in columns if col.get_text().strip()
#                 ]
#                 error_msg_info = (
#                     "Fehler: Keine Vertretung für MSS11 gefunden. MSS12 verfügbar"
#                 )
#                 print(colored(error_msg_info, "red"))
#         try:
#             ex_vertretung
#         except NameError:
#             error_msg = "Fehler: Keine Vertretung für MSS11 & MSS12 gefunden"
#             print(colored(error_msg, "red", attrs=["bold"]))
#             exit()


# ! Main Function:
def main():
    args = parse_args()
    global day
    day = args.day if args.day is not None else 1
    global verbose
    verbose = args.verbose if args.verbose is not None and args.verbose != 0 else 0

    if verbose == 1:
        global devnull
        devnull = open(os.devnull, "w")
        global old_stdout
        old_stdout = os.dup(1)
        os.dup2(devnull.fileno(), 1)

    # ? Prepare for scraping
    prep_check_internet()
    prep_API_URL()
    # ? Main webscraper
    act_future_list_check()
    act_main_vertretung()
    # ? Write to file / Website
    # aft_combiner()


if __name__ == "__main__":
    main()

# file_path = "vertretung.json"
# # print(json_string)
# try:
#     speicher_versuch(file_path, json_string)
#     try:
#         # Shell-Skript ausführen
#         # with open("/dev/null", "w") as devnull:
#         #    subprocess.check_call(
#         #        ["expect", "auto-ktk.de"], stdout=devnull, stderr=devnull
#         #    )
#         if verbose != 1:
#             print(colored("JSON wurde geuploaded!", "green", attrs=["bold"]))
#     except subprocess.CalledProcessError as e:
#         print(
#             colored(
#                 f"Fehler beim Ausführen des Shell-Skripts: {e}", "red", attrs=["bold"]
#             )
#         )
# except NameError:
#     if verbose == 1:
#         os.dup2(old_stdout, 1)
#         devnull.close()
#         print("Keine Vertretungen Verfügbar!")
#     else:
#         print(colored("Keine Vertretungen Verfügbar!", "yellow", attrs=["bold"]))
#     with open(file_path, "w") as f:
#         f.write('["Keine Vertretungen verfügbar!"]')
#     if verbose != 1:
#         print(
#             colored(
#                 "Info: Output in vertretung.json gespeichert.", "yellow", attrs=["bold"]
#             )
#         )


# try:
#     print(kombiniert)
# except NameError:
#     pass
