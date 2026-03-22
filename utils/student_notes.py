from threading import Lock

from utils.mysql_db import get_db_connection

_schema_lock = Lock()
_schema_ready = False


def ensure_student_notes_table():
    global _schema_ready
    if _schema_ready:
        return

    with _schema_lock:
        if _schema_ready:
            return

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS student_notes (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        topic_slug VARCHAR(120) NOT NULL,
                        note_text MEDIUMTEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_student_topic_notes (user_id, topic_slug),
                        CONSTRAINT fk_student_notes_user
                            FOREIGN KEY (user_id) REFERENCES users(id)
                            ON DELETE CASCADE
                    )
                    """
                )
            _schema_ready = True
        finally:
            connection.close()


def get_student_note(user_id, topic_slug):
    ensure_student_notes_table()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT note_text, updated_at
                FROM student_notes
                WHERE user_id = %s AND topic_slug = %s
                LIMIT 1
                """,
                (user_id, topic_slug),
            )
            return cursor.fetchone()
    finally:
        connection.close()


def save_student_note(user_id, topic_slug, note_text):
    ensure_student_notes_table()
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO student_notes (user_id, topic_slug, note_text)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    note_text = VALUES(note_text),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, topic_slug, note_text),
            )
    finally:
        connection.close()
