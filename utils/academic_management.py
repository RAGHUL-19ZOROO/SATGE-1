import csv
from io import TextIOWrapper
from pathlib import Path
from uuid import uuid4

from pymysql import MySQLError
from werkzeug.security import generate_password_hash

from utils.file_handler import ALLOWED_EXTENSIONS
from utils.mysql_db import get_db_connection


STAFF_NOTE_UPLOAD_DIR = Path("uploads/staff_notes")


def ensure_academic_schema():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS departments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    code VARCHAR(30) NOT NULL UNIQUE,
                    name VARCHAR(120) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS semesters (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    semester_no INT NOT NULL UNIQUE,
                    title VARCHAR(120) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS academic_subjects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    department_id INT NOT NULL,
                    semester_id INT NOT NULL,
                    subject_code VARCHAR(50) NOT NULL,
                    subject_name VARCHAR(150) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_academic_subject_department
                        FOREIGN KEY (department_id) REFERENCES departments(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_academic_subject_semester
                        FOREIGN KEY (semester_id) REFERENCES semesters(id)
                        ON DELETE CASCADE,
                    UNIQUE KEY uq_academic_subject (department_id, semester_id, subject_code)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS staff_assignments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    staff_user_id INT NOT NULL,
                    academic_subject_id INT NOT NULL,
                    class_name VARCHAR(80) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_staff_assignment_user
                        FOREIGN KEY (staff_user_id) REFERENCES users(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_staff_assignment_subject
                        FOREIGN KEY (academic_subject_id) REFERENCES academic_subjects(id)
                        ON DELETE CASCADE,
                    UNIQUE KEY uq_staff_assignment (staff_user_id, academic_subject_id, class_name)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS student_profiles (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    register_number VARCHAR(60) NULL,
                    department_id INT NOT NULL,
                    semester_id INT NOT NULL,
                    class_name VARCHAR(80) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_student_profile_user
                        FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_student_profile_department
                        FOREIGN KEY (department_id) REFERENCES departments(id)
                        ON DELETE CASCADE,
                    CONSTRAINT fk_student_profile_semester
                        FOREIGN KEY (semester_id) REFERENCES semesters(id)
                        ON DELETE CASCADE,
                    UNIQUE KEY uq_student_profile_user (user_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS staff_uploaded_notes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    staff_assignment_id INT NOT NULL,
                    topic_slug VARCHAR(120) NOT NULL,
                    unit_title VARCHAR(150) NOT NULL,
                    topic_title VARCHAR(150) NOT NULL,
                    note_title VARCHAR(150) NOT NULL,
                    original_file_name VARCHAR(255) NOT NULL,
                    stored_file_path VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_staff_note_assignment
                        FOREIGN KEY (staff_assignment_id) REFERENCES staff_assignments(id)
                        ON DELETE CASCADE
                )
                """
            )
    finally:
        connection.close()


def list_departments():
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, code, name, created_at
                FROM departments
                ORDER BY code ASC
                """
            )
            return cursor.fetchall() or []
    finally:
        connection.close()


def list_semesters():
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, semester_no, title, created_at
                FROM semesters
                ORDER BY semester_no ASC
                """
            )
            return cursor.fetchall() or []
    finally:
        connection.close()


def list_academic_subjects():
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    s.id,
                    s.subject_code,
                    s.subject_name,
                    d.code AS department_code,
                    d.name AS department_name,
                    sem.semester_no,
                    sem.title AS semester_title,
                    s.created_at
                FROM academic_subjects s
                INNER JOIN departments d ON d.id = s.department_id
                INNER JOIN semesters sem ON sem.id = s.semester_id
                ORDER BY d.code ASC, sem.semester_no ASC, s.subject_code ASC
                """
            )
            return cursor.fetchall() or []
    finally:
        connection.close()


def list_staff_assignments():
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sa.id,
                    u.full_name AS staff_name,
                    u.email AS staff_email,
                    d.code AS department_code,
                    sem.semester_no,
                    sem.title AS semester_title,
                    subj.subject_code,
                    subj.subject_name,
                    sa.class_name,
                    sa.created_at
                FROM staff_assignments sa
                INNER JOIN users u ON u.id = sa.staff_user_id
                INNER JOIN academic_subjects subj ON subj.id = sa.academic_subject_id
                INNER JOIN departments d ON d.id = subj.department_id
                INNER JOIN semesters sem ON sem.id = subj.semester_id
                ORDER BY sa.created_at DESC
                """
            )
            return cursor.fetchall() or []
    finally:
        connection.close()


def list_student_profiles():
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sp.id,
                    u.full_name AS student_name,
                    u.email AS student_email,
                    sp.register_number,
                    d.code AS department_code,
                    sem.semester_no,
                    sem.title AS semester_title,
                    sp.class_name,
                    sp.created_at
                FROM student_profiles sp
                INNER JOIN users u ON u.id = sp.user_id
                INNER JOIN departments d ON d.id = sp.department_id
                INNER JOIN semesters sem ON sem.id = sp.semester_id
                ORDER BY sp.created_at DESC
                """
            )
            return cursor.fetchall() or []
    finally:
        connection.close()


def list_staff_assignments_for_user(user_id):
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sa.id,
                    sa.class_name,
                    d.code AS department_code,
                    d.name AS department_name,
                    sem.semester_no,
                    sem.title AS semester_title,
                    subj.subject_code,
                    subj.subject_name
                FROM staff_assignments sa
                INNER JOIN academic_subjects subj ON subj.id = sa.academic_subject_id
                INNER JOIN departments d ON d.id = subj.department_id
                INNER JOIN semesters sem ON sem.id = subj.semester_id
                WHERE sa.staff_user_id = %s
                ORDER BY sem.semester_no ASC, subj.subject_code ASC, sa.class_name ASC
                """,
                (user_id,),
            )
            return cursor.fetchall() or []
    finally:
        connection.close()


def get_staff_assignment_for_user(assignment_id, user_id):
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sa.id,
                    sa.staff_user_id,
                    sa.class_name,
                    d.code AS department_code,
                    d.name AS department_name,
                    sem.semester_no,
                    sem.title AS semester_title,
                    subj.subject_code,
                    subj.subject_name
                FROM staff_assignments sa
                INNER JOIN academic_subjects subj ON subj.id = sa.academic_subject_id
                INNER JOIN departments d ON d.id = subj.department_id
                INNER JOIN semesters sem ON sem.id = subj.semester_id
                WHERE sa.id = %s AND sa.staff_user_id = %s
                LIMIT 1
                """,
                (assignment_id, user_id),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def list_notes_for_assignment(assignment_id):
    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, topic_slug, unit_title, topic_title, note_title, original_file_name, stored_file_path, created_at
                FROM staff_uploaded_notes
                WHERE staff_assignment_id = %s
                ORDER BY created_at DESC
                """,
                (assignment_id,),
            )
            return cursor.fetchall() or []
    finally:
        connection.close()


def create_department(code, name):
    cleaned_code = (code or "").strip().upper()
    cleaned_name = (name or "").strip()
    if not cleaned_code or not cleaned_name:
        raise ValueError("Department code and name are required.")

    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO departments (code, name) VALUES (%s, %s)",
                (cleaned_code, cleaned_name),
            )
    except MySQLError as exc:
        if "Duplicate" in str(exc):
            raise ValueError("Department code already exists.") from exc
        raise
    finally:
        connection.close()


def create_semester(semester_no, title):
    try:
        cleaned_no = int(semester_no)
    except (TypeError, ValueError) as exc:
        raise ValueError("Semester number must be a valid number.") from exc

    cleaned_title = (title or "").strip() or f"Semester {cleaned_no}"
    if cleaned_no <= 0:
        raise ValueError("Semester number must be greater than zero.")

    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO semesters (semester_no, title) VALUES (%s, %s)",
                (cleaned_no, cleaned_title),
            )
    except MySQLError as exc:
        if "Duplicate" in str(exc):
            raise ValueError("Semester already exists.") from exc
        raise
    finally:
        connection.close()


def create_academic_subject(department_id, semester_id, subject_code, subject_name):
    cleaned_code = (subject_code or "").strip().upper()
    cleaned_name = (subject_name or "").strip()
    if not department_id or not semester_id or not cleaned_code or not cleaned_name:
        raise ValueError("Department, semester, subject code, and subject name are required.")

    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO academic_subjects (department_id, semester_id, subject_code, subject_name)
                VALUES (%s, %s, %s, %s)
                """,
                (department_id, semester_id, cleaned_code, cleaned_name),
            )
    except MySQLError as exc:
        if "Duplicate" in str(exc):
            raise ValueError("That subject is already mapped for the selected department and semester.") from exc
        raise
    finally:
        connection.close()


def create_staff_assignment(full_name, email, password, academic_subject_id, class_name):
    cleaned_name = (full_name or "").strip()
    cleaned_email = (email or "").strip().lower()
    cleaned_class = (class_name or "").strip()
    if not cleaned_name or not cleaned_email or not password or not academic_subject_id or not cleaned_class:
        raise ValueError("Staff name, email, password, subject mapping, and class are required.")
    if "@" not in cleaned_email:
        raise ValueError("Enter a valid staff email.")
    if len(password) < 6:
        raise ValueError("Staff password must be at least 6 characters.")

    ensure_academic_schema()
    connection = get_db_connection()
    try:
        connection.begin()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, 'teacher', 1)
                """,
                (cleaned_name, cleaned_email, generate_password_hash(password)),
            )
            staff_user_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO staff_assignments (staff_user_id, academic_subject_id, class_name)
                VALUES (%s, %s, %s)
                """,
                (staff_user_id, academic_subject_id, cleaned_class),
            )
        connection.commit()
    except MySQLError as exc:
        connection.rollback()
        if "Duplicate" in str(exc):
            raise ValueError("Staff email or assignment already exists.") from exc
        raise
    finally:
        connection.close()


def import_students_csv(csv_file, department_id, semester_id, class_name):
    if not csv_file or not getattr(csv_file, "filename", ""):
        raise ValueError("Upload a CSV file with student data.")

    cleaned_class = (class_name or "").strip()
    if not department_id or not semester_id or not cleaned_class:
        raise ValueError("Department, semester, and class are required for student upload.")

    ensure_academic_schema()
    created = 0
    failed = []
    wrapper = TextIOWrapper(csv_file.stream, encoding="utf-8-sig", newline="")

    try:
        reader = csv.DictReader(wrapper)
        required_columns = {"full_name", "email", "password"}
        if not reader.fieldnames or not required_columns.issubset({(name or "").strip() for name in reader.fieldnames}):
            raise ValueError("CSV must include full_name, email, and password columns.")

        connection = get_db_connection()
        try:
            for index, row in enumerate(reader, start=2):
                full_name = (row.get("full_name") or "").strip()
                email = (row.get("email") or "").strip().lower()
                password = row.get("password") or ""
                register_number = (row.get("register_number") or "").strip()
                row_class = (row.get("class_name") or cleaned_class).strip() or cleaned_class

                if not full_name or not email or not password:
                    failed.append(f"Row {index}: missing full_name, email, or password.")
                    continue

                try:
                    connection.begin()
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            INSERT INTO users (full_name, email, password_hash, role, is_active)
                            VALUES (%s, %s, %s, 'student', 1)
                            """,
                            (full_name, email, generate_password_hash(password)),
                        )
                        user_id = cursor.lastrowid
                        cursor.execute(
                            """
                            INSERT INTO student_profiles (user_id, register_number, department_id, semester_id, class_name)
                            VALUES (%s, %s, %s, %s, %s)
                            """,
                            (user_id, register_number or None, department_id, semester_id, row_class),
                        )
                    connection.commit()
                    created += 1
                except MySQLError as exc:
                    connection.rollback()
                    failed.append(f"Row {index}: {str(exc)}")
        finally:
            connection.close()
    finally:
        wrapper.detach()

    return {"created": created, "failed": failed}


def save_staff_note(assignment_id, topic_slug, unit_title, topic_title, note_title, file_storage):
    cleaned_slug = (topic_slug or "").strip()
    cleaned_unit = (unit_title or "").strip()
    cleaned_topic = (topic_title or "").strip()
    cleaned_title = (note_title or "").strip() or cleaned_topic

    if not cleaned_slug or not cleaned_unit or not cleaned_topic:
        raise ValueError("Unit title, topic title, and topic slug are required.")

    if not file_storage or not file_storage.filename:
        raise ValueError("Select a TXT or PDF file to upload.")

    extension = Path(file_storage.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only TXT and PDF files are supported.")

    STAFF_NOTE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    stored_path = STAFF_NOTE_UPLOAD_DIR / stored_name
    file_storage.save(stored_path)

    ensure_academic_schema()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO staff_uploaded_notes
                (
                    staff_assignment_id,
                    topic_slug,
                    unit_title,
                    topic_title,
                    note_title,
                    original_file_name,
                    stored_file_path
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    assignment_id,
                    cleaned_slug,
                    cleaned_unit,
                    cleaned_topic,
                    cleaned_title,
                    file_storage.filename,
                    str(stored_path).replace("\\", "/"),
                ),
            )
    finally:
        connection.close()
