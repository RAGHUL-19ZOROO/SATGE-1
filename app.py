from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, url_for
from pymysql import MySQLError
from urllib.parse import urlparse
from pathlib import Path
import json
import uuid
from werkzeug.security import generate_password_hash

from config import FLASK_SECRET_KEY, SSL_CERT_FILE, SSL_KEY_FILE
from utils.auth import (
    admin_required,
    authenticate_user,
    current_user,
    login_required,
    login_user,
    logout_user,
    record_login_audit,
    teacher_required,
)
from utils.anna_curriculum import add_department, add_subject, get_curriculum
from utils.direct_messages import get_thread, list_dm_contacts, send_message
from utils.file_handler import (
    find_note_file,
    get_notes,
    list_topics,
    save_notes_for_topic_slug,
    save_uploaded_notes,
)
from utils.mysql_db import get_db_connection
from utils.student_notes import get_student_note, save_student_note
from utils.admin_catalog import add_admin_entry, get_admin_directory
from utils.notes_images import add_notes_image, get_notes_images
from utils.topic_mcq import (
    get_topic_access_map,
    get_topic_mcqs_for_student,
    get_topic_result,
    grade_mcq_attempt,
    save_attempt_result,
    save_topic_mcqs,
)
from utils.topic_text_content import get_text_content, save_text_content
from utils.topic_catalog import (
    create_topic,
    create_unit,
    get_course,
    get_default_topic,
    get_topic,
    get_topic_or_404,
    list_units,
)
from utils.wiki_summary import get_topic_summary

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(SSL_CERT_FILE and SSL_KEY_FILE)
app.config["SESSION_REFRESH_EACH_REQUEST"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 604800
APP_NAME = "Learning Paradiso"


def asset_version(relative_path):
    try:
        return int((Path("static") / relative_path).stat().st_mtime)
    except OSError:
        return 1


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "frame-src https://www.youtube.com https://www.youtube-nocookie.com; "
        "connect-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # Cache static assets aggressively to reduce repeat page-load time.
    if request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "public, max-age=604800, immutable"

    return response


def get_database_status():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS database_name")
            database_name = cursor.fetchone()["database_name"]
            cursor.execute("SELECT COUNT(*) AS total_users FROM users")
            total_users = cursor.fetchone()["total_users"]
        return {
            "connected": True,
            "database": database_name,
            "total_users": total_users,
        }
    finally:
        connection.close()


@app.context_processor
def inject_auth_state():
    return {
        "app_name": APP_NAME,
        "current_user": current_user(),
        "asset_version": asset_version,
    }


def list_admin_users():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, full_name, email, role, is_active, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT 200
                """
            )
            rows = cursor.fetchall() or []
    finally:
        connection.close()

    users = []
    for item in rows:
        role = str(item.get("role") or "").strip().lower()
        users.append(
            {
                "id": item.get("id"),
                "full_name": item.get("full_name"),
                "email": item.get("email"),
                "role": "staff" if role == "teacher" else role,
                "is_active": bool(item.get("is_active")),
                "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
            }
        )
    return users


def get_admin_users_payload():
    users = []
    user_error = ""
    try:
        users = list_admin_users()
    except MySQLError:
        user_error = "Unable to load user list from database."
    return users, user_error


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        role = current_user()["role"]
        if role == "staff":
            return redirect(url_for("staff_page"))
        if role == "admin":
            return redirect(url_for("admin_page"))
        return redirect(url_for("home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "").strip().lower()

        if role not in {"staff", "student", "admin"}:
            flash("Choose Student, Staff, or Admin.", "warning")
            return render_template("login.html")

        try:
            user = authenticate_user(email, password, role)
        except MySQLError:
            flash("Unable to connect to MySQL. Check your database configuration.", "warning")
            return render_template("login.html")

        if not user:
            flash("Invalid email, password, or role.", "warning")
            return render_template("login.html")

        login_user(user)
        record_login_audit(
            user["id"],
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
        )
        flash(f"Welcome back, {user['full_name']}.", "success")
        if user["role"] == "staff":
            return redirect(url_for("staff_page"))
        if user["role"] == "admin":
            return redirect(url_for("admin_page"))
        return redirect(url_for("home"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/db-check")
def db_check():
    try:
        return jsonify(get_database_status())
    except MySQLError as exc:
        return jsonify({"connected": False, "error": str(exc)}), 500


@app.route("/")
@login_required
def home():
    user = current_user()
    topic_access = {}
    if user and user.get("role") == "student":
        topic_access = get_topic_access_map(user["id"])

    return render_template(
        "home.html",
        course=get_course(),
        units=list_units(),
        default_topic=get_default_topic(),
        topic_access=topic_access,
    )


@app.route("/topic/<topic_slug>")
@login_required
def topic_page(topic_slug):
    topic = get_topic_or_404(topic_slug)
    user = current_user()
    course = get_course()
    topic_access = {}
    english_summary = ""
    tamil_summary = ""
    if user and user.get("role") == "student":
        topic_access = get_topic_access_map(user["id"])
        is_unlocked = topic_access.get(topic_slug, False)
        if not is_unlocked:
            flash("This topic is locked. Score above 80% in the previous topic MCQ to unlock it.", "warning")
            return redirect(url_for("home"))

        query_with_subject = f"{topic.get('title', '')} {course.get('title', '')}".strip()
        english_summary = get_topic_summary(query_with_subject, language="en") or get_topic_summary(
            topic.get("title", ""), language="en"
        )
        tamil_summary = get_topic_summary(query_with_subject, language="ta") or get_topic_summary(
            topic.get("title", ""), language="ta"
        )

    topic["has_notes"] = bool(get_notes(topic_slug))
    mcq_questions = get_topic_mcqs_for_student(topic_slug)
    topic_result = get_topic_result(user["id"], topic_slug) if user else {}

    return render_template(
        "topic.html",
        course=course,
        topic=topic,
        text_content=get_text_content(topic_slug),
        notes_images=get_notes_images(topic_slug),
        english_summary=english_summary,
        tamil_summary=tamil_summary,
        mcq_questions=mcq_questions,
        mcq_result=topic_result,
        topic_access=topic_access,
        units=list_units(),
        topics=list_topics(),
    )


@app.route("/staff")
@teacher_required
def staff_page():
    return render_template("staff.html", course=get_course())


@app.route("/staff/create-content")
@teacher_required
def staff_create_content_page():
    return render_template("staff_create_content.html", course=get_course(), topics=list_topics(), units=list_units())


@app.route("/staff/text-content/new")
@teacher_required
def staff_new_text_content_page():
    return render_template("staff_text_content_new.html", course=get_course(), topics=list_topics())


@app.route("/staff/text-content/update")
@teacher_required
def staff_update_text_content_page():
    return render_template("staff_text_content_update.html", course=get_course(), topics=list_topics())


@app.route("/staff/text-content", methods=["POST"])
@teacher_required
def save_text_content_route():
    data = request.get_json(silent=True) or {}
    topic_slug = (data.get("topic_slug") or "").strip()
    explanation = str(data.get("explanation") or "").strip()
    example = str(data.get("example") or "").strip()
    analogy = str(data.get("analogy") or "").strip()
    extra_fields = data.get("extra_fields") or []
    related_urls = data.get("related_urls") or []
    images = data.get("images") or []

    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Select a valid topic."}), 400

    if not isinstance(extra_fields, list):
        return jsonify({"error": "Extra fields must be a list."}), 400

    if not isinstance(related_urls, list):
        return jsonify({"error": "Related URLs must be a list."}), 400

    if not isinstance(images, list):
        return jsonify({"error": "Images must be a list."}), 400

    cleaned_extra_fields = []
    for item in extra_fields:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        value = str(item.get("value") or "").strip()
        if not label and not value:
            continue
        if not label or not value:
            return jsonify({"error": "Each extra field must include both label and value."}), 400
        if len(label) > 120 or len(value) > 4000:
            return jsonify({"error": "Extra field label/value is too long."}), 400
        cleaned_extra_fields.append({"label": label, "value": value})

    cleaned_related_urls = []
    for item in related_urls:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title and not url:
            continue
        if not url:
            return jsonify({"error": "Each related URL entry must include a URL."}), 400

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return jsonify({"error": f"Invalid URL: {url}"}), 400

        if len(title) > 200 or len(url) > 2000:
            return jsonify({"error": "Related URL title or URL is too long."}), 400

        cleaned_related_urls.append({"title": title, "url": url})

    cleaned_images = []
    for item in images:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if not title and not url:
            continue
        if not url:
            return jsonify({"error": "Each image entry must include a URL."}), 400

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return jsonify({"error": f"Invalid image URL: {url}"}), 400

        if len(title) > 200 or len(url) > 2000:
            return jsonify({"error": "Image title or URL is too long."}), 400

        cleaned_images.append({"title": title, "url": url})

    if not any([explanation, example, analogy, cleaned_extra_fields, cleaned_related_urls, cleaned_images]):
        return jsonify({"error": "Provide at least one text field, extra field, related URL, or image."}), 400

    for field_name, value in {
        "Explanation": explanation,
        "Example": example,
        "Analogy": analogy,
    }.items():
        if len(value) > 12000:
            return jsonify({"error": f"{field_name} is too long. Keep each field under 12,000 characters."}), 400

    save_text_content(topic_slug, explanation, example, analogy, cleaned_extra_fields, cleaned_related_urls, cleaned_images)
    return jsonify({"message": f"Text content saved for {topic['title']}."})


@app.route("/staff/text-content/<topic_slug>", methods=["GET"])
@teacher_required
def get_text_content_route(topic_slug):
    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Select a valid topic."}), 404

    return jsonify(
        {
            "topic": {
                "slug": topic["slug"],
                "title": topic["title"],
            },
            "text_content": get_text_content(topic_slug),
        }
    )


@app.route("/staff/text-content/image", methods=["POST"])
@teacher_required
def upload_text_content_image():
    image_file = request.files.get("image_file")
    image_title = str(request.form.get("title") or "").strip()

    if not image_file or not image_file.filename:
        return jsonify({"error": "Select an image file to upload."}), 400

    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    extension = Path(image_file.filename).suffix.lower()
    if extension not in allowed_extensions:
        return jsonify({"error": "Only PNG, JPG, JPEG, GIF, and WEBP are allowed."}), 400

    upload_dir = Path("static/uploads/text_content")
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{extension}"
    save_path = upload_dir / unique_name
    image_file.save(save_path)

    url = f"/static/uploads/text_content/{unique_name}"
    return jsonify(
        {
            "message": "Image uploaded successfully.",
            "image": {
                "title": image_title,
                "url": url,
            },
        }
    )


@app.route("/admin")
@admin_required
def admin_page():
    users, user_error = get_admin_users_payload()

    directory = get_admin_directory()
    curriculum = get_curriculum()

    return render_template(
        "admin.html",
        directory=directory,
        curriculum=curriculum,
        admin_users=users,
        admin_users_error=user_error,
        course=get_course(),
    )


@app.route("/admin/directory-page")
@admin_required
def admin_directory_page():
    return render_template(
        "admin_directory.html",
        directory=get_admin_directory(),
        course=get_course(),
    )


@app.route("/admin/curriculum-page")
@admin_required
def admin_curriculum_page():
    return render_template(
        "admin_curriculum.html",
        curriculum=get_curriculum(),
        course=get_course(),
    )


@app.route("/admin/users-page")
@admin_required
def admin_users_page():
    users, user_error = get_admin_users_payload()
    return render_template(
        "admin_users.html",
        admin_users=users,
        admin_users_error=user_error,
        course=get_course(),
    )


@app.route("/admin/directory", methods=["POST"])
@admin_required
def add_admin_directory_entry():
    data = request.get_json(silent=True) or {}
    section = (data.get("section") or "").strip()
    name = (data.get("name") or "").strip()
    details = str(data.get("details") or "").strip()

    if len(details) > 2000:
        return jsonify({"error": "Details are too long. Keep details under 2,000 characters."}), 400

    try:
        payload = add_admin_entry(section, name, details)
        return jsonify(
            {
                "message": f"{payload['entry']['name']} added under {payload['section']}.",
                "entry": payload["entry"],
                "section": payload["section"],
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/admin/curriculum/department", methods=["POST"])
@admin_required
def add_curriculum_department():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()

    try:
        entry = add_department(code, name)
        return jsonify({"message": f"Department {entry['code']} created.", "department": entry})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/admin/curriculum/subject", methods=["POST"])
@admin_required
def add_curriculum_subject():
    data = request.get_json(silent=True) or {}
    department_slug = (data.get("department_slug") or "").strip()
    subject_code = (data.get("subject_code") or "").strip()
    title = (data.get("title") or "").strip()
    semester = (data.get("semester") or "").strip()

    try:
        entry = add_subject(department_slug, subject_code, title, semester)
        return jsonify({"message": f"Subject {entry['subject_code']} added.", "subject": entry})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/admin/users", methods=["POST"])
@admin_required
def create_user_account():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().lower()

    if not full_name:
        return jsonify({"error": "Full name is required."}), 400
    if not email:
        return jsonify({"error": "Email is required."}), 400
    if "@" not in email:
        return jsonify({"error": "Enter a valid email."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if role not in {"staff", "student"}:
        return jsonify({"error": "Role must be staff or student."}), 400

    db_role = "teacher" if role == "staff" else role
    password_hash = generate_password_hash(password)

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (full_name, email, password_hash, db_role, 1),
            )
    except MySQLError as exc:
        message = str(exc)
        if "Duplicate" in message or "duplicate" in message:
            return jsonify({"error": "Email already exists."}), 400
        return jsonify({"error": "Unable to create user account."}), 500
    finally:
        connection.close()

    return jsonify({"message": f"{role.title()} account created for {full_name}."})


@app.route("/dm")
@login_required
def dm_page():
    return render_template("dm.html", course=get_course())


@app.route("/dm/contacts", methods=["GET"])
@login_required
def dm_contacts():
    contacts = list_dm_contacts(current_user())
    return jsonify({"contacts": contacts})


@app.route("/dm/thread/<int:contact_id>", methods=["GET"])
@login_required
def dm_thread(contact_id):
    contacts = list_dm_contacts(current_user())
    contact = next((item for item in contacts if int(item["id"]) == int(contact_id)), None)
    if not contact:
        return jsonify({"error": "Select a valid contact."}), 404

    return jsonify(
        {
            "contact": contact,
            "messages": get_thread(current_user(), contact_id),
        }
    )


@app.route("/dm/thread/<int:contact_id>", methods=["POST"])
@login_required
def dm_send(contact_id):
    data = request.get_json(silent=True) or {}
    message = str(data.get("message") or "").strip()

    contacts = list_dm_contacts(current_user())
    contact = next((item for item in contacts if int(item["id"]) == int(contact_id)), None)
    if not contact:
        return jsonify({"error": "Select a valid contact."}), 404

    try:
        payload = send_message(current_user(), contact, message)
        return jsonify({"message": "Message sent.", "item": payload})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/student-notes/<topic_slug>", methods=["GET"])
@login_required
def student_notes(topic_slug):
    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Unknown topic."}), 404

    user = current_user()
    note = get_student_note(user["id"], topic_slug)
    return jsonify(
        {
            "topic": topic_slug,
            "notes": (note or {}).get("note_text", ""),
            "updated_at": (note or {}).get("updated_at").isoformat() if (note or {}).get("updated_at") else None,
        }
    )


@app.route("/student-notes/<topic_slug>", methods=["POST"])
@login_required
def save_student_notes_route(topic_slug):
    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Unknown topic."}), 404

    data = request.get_json(silent=True) or {}
    note_text = str(data.get("notes") or "")

    if len(note_text) > 20000:
        return jsonify({"error": "Notes are too long. Keep them under 20,000 characters."}), 400

    user = current_user()
    save_student_note(user["id"], topic_slug, note_text)
    note = get_student_note(user["id"], topic_slug)

    return jsonify(
        {
            "message": "Your notes have been saved.",
            "topic": topic_slug,
            "notes": note_text,
            "updated_at": (note or {}).get("updated_at").isoformat() if (note or {}).get("updated_at") else None,
        }
    )


@app.route("/upload", methods=["POST"])
@teacher_required
def upload():
    topic_name = (request.form.get("topic_name") or "").strip()
    file = request.files.get("notes_file")

    if not topic_name:
        return jsonify({"error": "Topic name is required."}), 400

    if not file or not file.filename:
        return jsonify({"error": "Select a TXT or PDF file to upload."}), 400

    try:
        saved_topic = save_uploaded_notes(topic_name, file)
        topic = get_topic(saved_topic)
        return jsonify(
            {
                "message": f"Notes uploaded for {topic['title'] if topic else topic_name}.",
                "topic": saved_topic,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/staff/notes-image", methods=["POST"])
@teacher_required
def upload_notes_image():
    topic_slug = (request.form.get("topic_slug") or "").strip()
    image_title = str(request.form.get("title") or "").strip()
    image_file = request.files.get("image_file")

    if not topic_slug:
        return jsonify({"error": "Select a topic."}), 400

    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Select a valid topic."}), 400

    if not image_file or not image_file.filename:
        return jsonify({"error": "Select an image file to upload."}), 400

    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    extension = Path(image_file.filename).suffix.lower()
    if extension not in allowed_extensions:
        return jsonify({"error": "Only PNG, JPG, JPEG, GIF, and WEBP are allowed."}), 400

    upload_dir = Path("static/uploads/notes_images")
    upload_dir.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{extension}"
    save_path = upload_dir / unique_name
    image_file.save(save_path)

    url = f"/static/uploads/notes_images/{unique_name}"
    entry = add_notes_image(topic_slug, image_title, url)
    return jsonify(
        {
            "message": "Notes image uploaded successfully.",
            "image": entry,
            "topic": topic_slug,
        }
    )


@app.route("/staff/mcq-upload", methods=["POST"])
@teacher_required
def upload_topic_mcq():
    topic_slug = (request.form.get("topic_slug") or "").strip()
    mcq_file = request.files.get("mcq_file")

    if not topic_slug:
        return jsonify({"error": "Select a topic."}), 400

    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Select a valid topic."}), 400

    if not mcq_file or not mcq_file.filename:
        return jsonify({"error": "Upload a JSON file."}), 400

    extension = Path(mcq_file.filename).suffix.lower()
    if extension != ".json":
        return jsonify({"error": "Only JSON files are supported for MCQ upload."}), 400

    try:
        payload = json.load(mcq_file.stream)
    except Exception:
        return jsonify({"error": "Invalid JSON file."}), 400

    try:
        questions = save_topic_mcqs(topic_slug, payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(
        {
            "message": f"MCQ uploaded for {topic['title']}.",
            "topic": topic_slug,
            "total_questions": len(questions),
        }
    )


@app.route("/topic/<topic_slug>/mcq", methods=["GET"])
@login_required
def topic_mcq(topic_slug):
    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Unknown topic."}), 404

    user = current_user()
    if user.get("role") == "student":
        topic_access = get_topic_access_map(user["id"])
        if not topic_access.get(topic_slug, False):
            return jsonify({"error": "Topic is locked. Pass previous topic MCQ with more than 80% to unlock."}), 403

    return jsonify(
        {
            "topic": topic_slug,
            "questions": get_topic_mcqs_for_student(topic_slug),
            "result": get_topic_result(user["id"], topic_slug),
        }
    )


@app.route("/topic/<topic_slug>/mcq-attempt", methods=["POST"])
@login_required
def topic_mcq_attempt(topic_slug):
    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Unknown topic."}), 404

    user = current_user()
    if user.get("role") != "student":
        return jsonify({"error": "Only students can submit MCQ attempts."}), 403

    topic_access = get_topic_access_map(user["id"])
    if not topic_access.get(topic_slug, False):
        return jsonify({"error": "Topic is locked. Pass previous topic MCQ with more than 80% to unlock."}), 403

    data = request.get_json(silent=True) or {}
    answers = data.get("answers") or []

    try:
        result = grade_mcq_attempt(topic_slug, answers)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    saved = save_attempt_result(user["id"], topic_slug, result)
    return jsonify(
        {
            "message": "MCQ submitted.",
            "result": {
                **result,
                "best_score": saved["best_score"],
            },
        }
    )


@app.route("/staff/unit", methods=["POST"])
@teacher_required
def create_unit_route():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()

    try:
        unit = create_unit(title)
        return jsonify({"message": f"{unit['title']} created successfully.", "unit": unit})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/staff/topic", methods=["POST"])
@teacher_required
def create_topic_route():
    unit_slug = (request.form.get("unit_slug") or "").strip()
    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    youtube_url = (request.form.get("youtube_url") or "").strip()
    no_video = (request.form.get("no_video") or "").strip().lower() in {"1", "true", "on", "yes"}
    notes_file = request.files.get("notes_file")

    try:
        topic = create_topic(unit_slug, title, description, youtube_url, no_video=no_video)
        if notes_file and notes_file.filename:
            save_notes_for_topic_slug(topic["slug"], notes_file)

        return jsonify(
            {
                "message": f"{topic['title']} created successfully.",
                "topic": topic,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/download/<topic_slug>")
@login_required
def download_notes(topic_slug):
    path = find_note_file(topic_slug)
    if not path:
        return jsonify({"error": "Notes not found for this topic."}), 404
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    ssl_context = None
    if SSL_CERT_FILE and SSL_KEY_FILE:
        ssl_context = (SSL_CERT_FILE, SSL_KEY_FILE)

    app.run(debug=True, threaded=True, ssl_context=ssl_context)
