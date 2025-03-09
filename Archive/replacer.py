import re
import json
from typing import Dict, Any

# Constants
SUBJECTS = {
    "L": "Latein",
    "Gr": "Griechisch",
    "M": "Mathe",
    "Mu": "Musik",
    "Bi": "Biologie",
    "Ch": "Chemie",
    "Ek": "Erdkunde",
    "Sport": "Sport",
    "Ge": "Geschichte",
    "kR": "kath. Reli",
    "D": "Deutsch",
    "eR": "ev. Reli",
    "et": "Ethik",
    "E": "Englisch",
    "Fr": "Französisch",
    "Ph": "Physik",
    "Inf": "Informatik",
    "Sk": "Sozialkunde",
    "BK": "Kunst",
}

FILE_PATHS = {
    "input": "json/teacher_replaced.json",
    "output": "json/änderung.json"
}


def load_json(file_path: str) -> Dict[str, Any]:
    """Load JSON data from a file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Dictionary containing the JSON data
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """Save data to a JSON file.

    Args:
        data: Dictionary to save
        file_path: Path where to save the JSON file
    """
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def normalize_string(text: str) -> str:
    """Normalize string by removing numbers and converting to lowercase.

    Args:
        text: String to normalize

    Returns:
        Normalized string
    """
    return re.sub(r"\d+", "", text).lower()


def get_subject_prefix(subject: str) -> str:
    """Determine subject prefix based on case.

    Args:
        subject: Subject string to analyze

    Returns:
        Appropriate prefix (LK, GK, or empty string)
    """
    if subject.isupper():
        return "LK"
    if subject.islower():
        return "GK"
    return ""


def update_subjects(data: Dict[str, Any], subject_mapping: Dict[str, str]) -> Dict[str, Any]:
    """Update subjects in the data structure with proper prefixes.

    Args:
        data: Data structure containing subjects to update
        subject_mapping: Dictionary mapping subject codes to full names

    Returns:
        Updated data structure
    """
    normalized_mapping = {normalize_string(
        k): v for k, v in subject_mapping.items()}

    for substitution in data.get("substitution", []):
        for item in substitution.get("content", []):
            if "subject" not in item:
                continue

            original = item["subject"]
            normalized_subject = normalize_string(original)

            if normalized_subject not in normalized_mapping:
                continue

            prefix = get_subject_prefix(original)
            new_value = normalized_mapping[normalized_subject]

            if prefix:
                new_value = f"{prefix} {new_value}"

            item["subject"] = new_value
            print(f"CHANGE: subject: changed '{original}' to '{new_value}'")

    return data


def main():
    try:
        data = load_json(FILE_PATHS["input"])
        updated_data = update_subjects(data, SUBJECTS)
        save_json(updated_data, FILE_PATHS["output"])
        print("JSON successfully updated!")
    except Exception as e:
        print(f"Error processing JSON: {str(e)}")


if __name__ == "__main__":
    main()
