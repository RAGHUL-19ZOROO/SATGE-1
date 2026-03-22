from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from utils.topic_catalog import list_topics as list_catalog_topics

UPLOADS_DIR = Path("uploads")
ALLOWED_EXTENSIONS = {".txt", ".pdf"}


def slugify_topic(topic_name):
    cleaned = secure_filename((topic_name or "").strip().lower())
    return cleaned.replace("-", "_")


def list_topics():
    topics = []
    for topic in list_catalog_topics():
        item = topic.copy()
        item["has_notes"] = bool(get_notes(item["slug"]))
        topics.append(item)
    return topics


def find_note_file(topic_slug):
    for extension in (".txt", ".pdf"):
        path = UPLOADS_DIR / f"{topic_slug}{extension}"
        if path.exists():
            return path
    return None


def get_notes(topic_slug):
    path = find_note_file(topic_slug)
    if not path:
        return ""

    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    return _extract_text_from_pdf(path.read_bytes())


def _extract_text_from_pdf(raw_bytes):
    reader = PdfReader(BytesIO(raw_bytes))
    text_parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            text_parts.append(text.strip())
    return "\n\n".join(text_parts).strip()


def save_uploaded_notes(topic_name, file_storage: FileStorage):
    if not topic_name:
        raise ValueError("Topic name is required.")

    if not file_storage or not file_storage.filename:
        raise ValueError("File is required.")

    topic_slug = slugify_topic(topic_name)
    extension = Path(file_storage.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only TXT and PDF files are supported.")

    valid_topics = {topic["slug"] for topic in list_catalog_topics()}
    if topic_slug not in valid_topics:
        raise ValueError("Upload is allowed only for the configured Operating Systems topics.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    for existing_extension in ALLOWED_EXTENSIONS:
        existing_path = UPLOADS_DIR / f"{topic_slug}{existing_extension}"
        if existing_path.exists():
            existing_path.unlink()

    target = UPLOADS_DIR / f"{topic_slug}{extension}"
    file_storage.save(target)
    return topic_slug


def save_notes_for_topic_slug(topic_slug, file_storage: FileStorage):
    if not topic_slug:
        raise ValueError("Topic slug is required.")

    if not file_storage or not file_storage.filename:
        raise ValueError("File is required.")

    extension = Path(file_storage.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only TXT and PDF files are supported.")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    for existing_extension in ALLOWED_EXTENSIONS:
        existing_path = UPLOADS_DIR / f"{topic_slug}{existing_extension}"
        if existing_path.exists():
            existing_path.unlink()

    target = UPLOADS_DIR / f"{topic_slug}{extension}"
    file_storage.save(target)
    return topic_slug
