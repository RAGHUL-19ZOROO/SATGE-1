"""Subject management utility module for handling subject/course operations."""

from utils.mysql_db import get_db_connection


def get_all_subjects():
    """Get all subjects from the database."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, code, description, created_at
                FROM subjects
                ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall() or []
    finally:
        connection.close()

    subjects = []
    for item in rows:
        subjects.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "code": item.get("code"),
                "description": item.get("description"),
                "created_at": item.get("created_at").isoformat()
                if item.get("created_at")
                else None,
            }
        )
    return subjects


def get_subject_by_id(subject_id):
    """Get a single subject by ID."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, code, description, created_at
                FROM subjects
                WHERE id = %s
                """,
                (subject_id,),
            )
            row = cursor.fetchone()
    finally:
        connection.close()

    if not row:
        return None

    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "code": row.get("code"),
        "description": row.get("description"),
        "created_at": row.get("created_at").isoformat()
        if row.get("created_at")
        else None,
    }


def add_subject(name, code, description=""):
    """Add a new subject to the database.
    
    Args:
        name: Subject name (e.g., "Operating Systems")
        code: Subject code (e.g., "OS")
        description: Optional subject description
        
    Returns:
        dict with subject details including id, or None if failed
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO subjects (name, code, description)
                VALUES (%s, %s, %s)
                """,
                (name, code, description or ""),
            )
            connection.commit()
            subject_id = cursor.lastrowid

        return get_subject_by_id(subject_id)
    except Exception:
        connection.rollback()
        return None
    finally:
        connection.close()


def update_subject(subject_id, name=None, code=None, description=None):
    """Update an existing subject.
    
    Args:
        subject_id: ID of subject to update
        name: New subject name (optional)
        code: New subject code (optional)
        description: New description (optional)
        
    Returns:
        dict with updated subject details, or None if failed
    """
    # Get current values
    current = get_subject_by_id(subject_id)
    if not current:
        return None

    # Use provided values or keep existing ones
    final_name = name if name is not None else current["name"]
    final_code = code if code is not None else current["code"]
    final_description = description if description is not None else current["description"]

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE subjects
                SET name = %s, code = %s, description = %s
                WHERE id = %s
                """,
                (final_name, final_code, final_description, subject_id),
            )
            connection.commit()

        return get_subject_by_id(subject_id)
    except Exception:
        connection.rollback()
        return None
    finally:
        connection.close()


def delete_subject(subject_id):
    """Delete a subject by ID.
    
    Args:
        subject_id: ID of subject to delete
        
    Returns:
        True if deletion successful, False otherwise
    """
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
            connection.commit()
            return cursor.rowcount > 0
    except Exception:
        connection.rollback()
        return False
    finally:
        connection.close()
