from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from pymysql import MySQLError

from agents.assessment_agent import evaluate_answers
from agents.doubt_agent import solve_doubt
from agents.learning_agent import generate_learning_package
from config import FLASK_SECRET_KEY, SSL_CERT_FILE, SSL_KEY_FILE
from utils.auth import (
    authenticate_user,
    current_user,
    login_required,
    login_user,
    logout_user,
    record_login_audit,
    teacher_required,
)
from utils.file_handler import (
    find_note_file,
    get_notes,
    list_topics,
    save_notes_for_topic_slug,
    save_uploaded_notes,
)
from utils.mysql_db import get_db_connection
from utils.student_notes import get_student_note, save_student_note
from utils.topic_catalog import (
    create_topic,
    create_unit,
    get_course,
    get_default_topic,
    get_topic,
    get_topic_or_404,
    list_units,
)

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(SSL_CERT_FILE and SSL_KEY_FILE)
app.config["SESSION_REFRESH_EACH_REQUEST"] = False


def _format_model_error(exc):
    message = str(exc)
    lowered = message.lower()

    if "no endpoints available matching your guardrail restrictions and data policy" in lowered:
        return (
            "OpenRouter blocked the selected model because of your privacy settings. "
            "Use a privacy-compatible model such as openai/gpt-4o-mini, or update "
            "your OpenRouter privacy settings at https://openrouter.ai/settings/privacy.",
            502,
        )

    if "quota" in lowered or "rate limit" in lowered or "429" in message:
        return (
            "The AI provider is rate-limited right now. Try again in a moment.",
            429,
        )

    if "401" in message or "unauthorized" in lowered or "invalid" in lowered:
        return (
            "The API key was rejected. Check OPENROUTER_API_KEY in the .env file.",
            401,
        )

    return message, 500


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
    return {"current_user": current_user()}


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("staff_page" if current_user()["role"] == "teacher" else "home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "").strip().lower()

        if role not in {"teacher", "student"}:
            flash("Choose either Teacher or Student.", "warning")
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
        return redirect(url_for("staff_page" if user["role"] == "teacher" else "home"))

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
    return render_template(
        "home.html",
        course=get_course(),
        units=list_units(),
        default_topic=get_default_topic(),
    )


@app.route("/topic/<topic_slug>")
@login_required
def topic_page(topic_slug):
    topic = get_topic_or_404(topic_slug)
    topic["has_notes"] = bool(get_notes(topic_slug))
    return render_template(
        "topic.html",
        course=get_course(),
        topic=topic,
        units=list_units(),
        topics=list_topics(),
    )


@app.route("/staff")
@teacher_required
def staff_page():
    return render_template("staff.html", course=get_course(), topics=list_topics(), units=list_units())


@app.route("/learn", methods=["POST"])
@login_required
def learn():
    data = request.get_json(silent=True) or {}
    topic_slug = (data.get("topic") or "").strip()

    if not topic_slug:
        return jsonify({"error": "Topic is required."}), 400

    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Unknown topic."}), 404

    try:
        notes = get_notes(topic_slug)
        lesson_package = generate_learning_package(topic, notes)
        session["assessment_bank"] = {
            "topic": topic_slug,
            "mcqs": lesson_package["mcqs"],
        }
        public_mcqs = [
            {
                "id": item["id"],
                "question": item["question"],
                "options": item["options"],
            }
            for item in lesson_package["mcqs"]
        ]
        response_payload = lesson_package.copy()
        response_payload["mcqs"] = public_mcqs
        return jsonify(response_payload)
    except Exception as exc:
        message, status_code = _format_model_error(exc)
        return jsonify({"error": message}), status_code


@app.route("/doubt", methods=["POST"])
@login_required
def doubt():
    data = request.get_json(silent=True) or {}
    topic_slug = (data.get("topic") or "").strip()
    question = (data.get("question") or "").strip()

    if not topic_slug:
        return jsonify({"error": "Topic is required."}), 400

    if not question:
        return jsonify({"error": "Question is required."}), 400

    topic = get_topic(topic_slug)
    if not topic:
        return jsonify({"error": "Unknown topic."}), 404

    try:
        notes = get_notes(topic_slug)
        answer = solve_doubt(question, topic, notes)
        return jsonify(answer)
    except Exception as exc:
        message, status_code = _format_model_error(exc)
        return jsonify({"error": message}), status_code


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


@app.route("/test", methods=["POST"])
@login_required
def test():
    data = request.get_json(silent=True) or {}
    topic_slug = (data.get("topic") or "").strip()
    answers = data.get("answers") or {}

    if not topic_slug:
        return jsonify({"error": "Topic is required."}), 400

    bank = session.get("assessment_bank") or {}
    if bank.get("topic") != topic_slug or not bank.get("mcqs"):
        return jsonify({"error": "Load the lesson before submitting the test."}), 400

    try:
        result = evaluate_answers(bank["mcqs"], answers)
        return jsonify(result)
    except Exception as exc:
        message, status_code = _format_model_error(exc)
        return jsonify({"error": message}), status_code


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
