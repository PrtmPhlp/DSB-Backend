import json

# Pfad zur Eingabe- und Ausgabedatei
input_file_path = "vertretung.json"
output_file_path = "ausgeschrieben.json"

# Öffne die Eingabedatei und lade den JSON-Inhalt
try:
    with open(input_file_path, "r", encoding="utf-8") as input_file:
        data = json.load(input_file)
except FileNotFoundError:
    print(f"Die Datei '{input_file_path}' wurde nicht gefunden.")
    exit()

# Überprüfe, ob die Eingabedatei "Zeile" Gruppen enthält
if isinstance(data, list):
    cleaned_data = []

    for item in data:
        if isinstance(item, list) and "MSS11" in item:
            # Entferne "MSS11" aus der "Zeile" Gruppe
            item.remove("MSS11")
        cleaned_data.append(item)

    # Speichere die bereinigten Daten in die Ausgabedatei
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        json.dump(cleaned_data, output_file, ensure_ascii=False, indent=4)

    print(f"Erfolgreich 'MSS11' entfernt und in '{output_file_path}' gespeichert.")
else:
    print("Die Datei enthält keine 'Zeile' Gruppen.")
