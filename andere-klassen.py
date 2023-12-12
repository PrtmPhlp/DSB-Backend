def andere_klassen():
    for klasse in [
        "5a",
        "5b",
        "5c",
        "6a",
        "6b",
        "6c",
        "7a",
        "7b",
        "7c",
        "8a",
        "8b",
        "8c",
        "9a",
        "9b",
        "9c",
        "MSS11",
        "10b",
    ]:
        print(f"Info: Checking for Vertretung in Klasse {klasse}")

        found = False
        for row in table.find_all("tr"):
            columns = row.find_all("td")
            if columns and columns[0].get_text().strip() == klasse:
                vertretung = [
                    col.get_text().strip() for col in columns if col.get_text().strip()
                ]
                print(colored(vertretung, "green", attrs=["bold"]))
                found = True

        if not found:
            error_msg = (
                f"Fehler: Keine Vertretungsinformationen gefunden für Klasse {klasse}."
            )
            print(colored(error_msg, "red", attrs=["bold"]))
