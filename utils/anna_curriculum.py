import json
from pathlib import Path

from werkzeug.utils import secure_filename


DATA_PATH = Path("data/anna_curriculum.json")
DEFAULT_DATA = {
    "departments": [],
    "subjects": [],
}


def _slugify(value):
    return secure_filename((value or "").strip().lower()).replace("-", "_")


def _load_data():
    if not DATA_PATH.exists():
        return {
            "departments": [],
            "subjects": [],
        }

    with DATA_PATH.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        return {
            "departments": [],
            "subjects": [],
        }

    departments = payload.get("departments") if isinstance(payload.get("departments"), list) else []
    subjects = payload.get("subjects") if isinstance(payload.get("subjects"), list) else []
    return {
        "departments": departments,
        "subjects": subjects,
    }


def _save_data(payload):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def get_curriculum():
    payload = _load_data()
    departments = [item for item in payload["departments"] if isinstance(item, dict)]
    subjects = [item for item in payload["subjects"] if isinstance(item, dict)]

    department_by_slug = {item.get("slug"): item for item in departments}
    hydrated_subjects = []
    for item in subjects:
        department_slug = str(item.get("department_slug") or "").strip()
        department = department_by_slug.get(department_slug) or {}
        hydrated_subjects.append(
            {
                "slug": str(item.get("slug") or "").strip(),
                "department_slug": department_slug,
                "department_code": str(department.get("code") or "").strip(),
                "department_name": str(department.get("name") or "").strip(),
                "subject_code": str(item.get("subject_code") or "").strip(),
                "title": str(item.get("title") or "").strip(),
                "semester": str(item.get("semester") or "").strip(),
            }
        )

    return {
        "departments": departments,
        "subjects": hydrated_subjects,
    }


def add_department(code, name):
    cleaned_code = str(code or "").strip().upper()
    cleaned_name = str(name or "").strip()

    if not cleaned_code:
        raise ValueError("Department code is required.")
    if not cleaned_name:
        raise ValueError("Department name is required.")

    payload = _load_data()
    departments = payload["departments"]

    if any(str(item.get("code") or "").strip().upper() == cleaned_code for item in departments):
        raise ValueError("Department code already exists.")

    slug = _slugify(cleaned_code)
    if any(str(item.get("slug") or "").strip() == slug for item in departments):
        raise ValueError("Department already exists.")

    entry = {
        "slug": slug,
        "code": cleaned_code,
        "name": cleaned_name,
    }
    departments.append(entry)
    _save_data(payload)
    return entry


def add_subject(department_slug, subject_code, title, semester=""):
    cleaned_department_slug = str(department_slug or "").strip()
    cleaned_subject_code = str(subject_code or "").strip().upper()
    cleaned_title = str(title or "").strip()
    cleaned_semester = str(semester or "").strip()

    if not cleaned_department_slug:
        raise ValueError("Select a department.")
    if not cleaned_subject_code:
        raise ValueError("Subject code is required.")
    if not cleaned_title:
        raise ValueError("Subject title is required.")

    payload = _load_data()
    departments = payload["departments"]
    if not any(str(item.get("slug") or "").strip() == cleaned_department_slug for item in departments):
        raise ValueError("Select a valid department.")

    subjects = payload["subjects"]
    if any(str(item.get("subject_code") or "").strip().upper() == cleaned_subject_code for item in subjects):
        raise ValueError("Subject code already exists.")

    slug = _slugify(cleaned_subject_code)
    entry = {
        "slug": slug,
        "department_slug": cleaned_department_slug,
        "subject_code": cleaned_subject_code,
        "title": cleaned_title,
        "semester": cleaned_semester,
    }
    subjects.append(entry)
    _save_data(payload)
    return entry
