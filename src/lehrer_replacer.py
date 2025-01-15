import json
from typing import Dict, Any


def load_json(file_path: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data: Dict[str, Any], file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def replace_teacher_codes(data: Dict[str, Any], teacher_mapping: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
   for substitution in data.get("substitution", []):
       for item in substitution.get("content", []):
           if "teacher" in item:
               code = item["teacher"]
               clean_code = code.strip('()')
               
               if clean_code in teacher_mapping:
                   old_value = item["teacher"]
                   name = teacher_mapping[clean_code]['Nachname']
                   # Put name in parentheses if original code was in parentheses
                   item["teacher"] = f"({name})" if code.startswith('(') else name
                   print(f"CHANGE: teacher: changed '{old_value}' to '{item['teacher']}'")
   return data


# Updated file path in the main function
def main():
    try:
        input_path = "json/formatted.json"
        teachers_path = "json/lehrer.json"
        output_path = "json/teacher_replaced.json"

        data = load_json(input_path)
        teachers = load_json(teachers_path)
        updated_data = replace_teacher_codes(data, teachers)
        save_json(updated_data, output_path)
        print("JSON successfully updated!")
    except Exception as e:
        print(f"Error processing JSON: {str(e)}")


if __name__ == "__main__":
    main()
