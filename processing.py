import json


def update_vertretung(vertretung_file, lehrer_file):
    # Laden der Dateien
    with open("vertretung.json", 'r', encoding='utf-8') as file:
        vertretung = json.load(file)

    with open(lehrer_file, 'r', encoding='utf-8') as file:
        lehrer = json.load(file)

    # Entfernen von "MSS11" und Ersetzen der Kürzel (auch in Klammern)
    updated_vertretung = []
    for item in vertretung:
        # Überspringen von "MSS11"
        if item == "MSS11":
            continue

        # Prüfen, ob das Element Kürzel in Klammern enthält
        if item.startswith('(') and item.endswith(')') and item[1:-1] in lehrer:
            voller_name = list(lehrer[item[1:-1]].keys())[0]
            updated_vertretung.append(f"({voller_name})")
        elif item in lehrer:
            voller_name = list(lehrer[item].keys())[0]
            updated_vertretung.append(voller_name)
        else:
            updated_vertretung.append(item)

    # Zurückschreiben der veränderten Daten
    with open(vertretung_file, 'w', encoding='utf-8') as file:
        json.dump(updated_vertretung, file, ensure_ascii=False, indent=4)

    return updated_vertretung


# Anwendung der Funktion
updated_vertretung = update_vertretung('ausgeschrieben.json', 'lehrer.json')
print(updated_vertretung)
