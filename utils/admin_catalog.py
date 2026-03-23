import json
from pathlib import Path

from werkzeug.utils import secure_filename


DATA_PATH = Path("data/admin_directory.json")
DEFAULT_DIRECTORY = {
    "semester": [],
    "courses": [],
    "staff": [],
    "student": [],
}


def _slugify(value):
    return secure_filename((value or "").strip().lower()).replace("-", "_")


def _load_directory():
    if not DATA_PATH.exists():
        return DEFAULT_DIRECTORY.copy()

    with DATA_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        return DEFAULT_DIRECTORY.copy()

    directory = DEFAULT_DIRECTORY.copy()
    for key in directory:
        value = data.get(key)
        directory[key] = value if isinstance(value, list) else []
    return directory


def _save_directory(directory):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(directory, file, indent=2)


def get_admin_directory():
    return _load_directory()


def add_admin_entry(section, name, details=""):
    normalized_section = (section or "").strip().lower()
    if normalized_section not in DEFAULT_DIRECTORY:
        raise ValueError("Select a valid section.")

    cleaned_name = (name or "").strip()
    cleaned_details = (details or "").strip()

    if not cleaned_name:
        raise ValueError("Name is required.")

    directory = _load_directory()
    entries = directory[normalized_section]
    slug = _slugify(cleaned_name)

    if any(item.get("slug") == slug for item in entries):
        raise ValueError(f"{cleaned_name} already exists in {normalized_section}.")

    entries.append(
        {
            "slug": slug,
            "name": cleaned_name,
            "details": cleaned_details,
        }
    )
    _save_directory(directory)

    return {
        "section": normalized_section,
        "entry": entries[-1],
    }
