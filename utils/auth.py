from functools import wraps

from flask import flash, redirect, session, url_for
from pymysql import MySQLError
from werkzeug.security import check_password_hash

from utils.mysql_db import get_db_connection


LOCKED_LOGIN_EMAIL = "thiru@gmail.com"
LOCKED_LOGIN_PASSWORD = "1234"


def _normalize_role(role):
    cleaned = (role or "").strip().lower()
    return "staff" if cleaned == "teacher" else cleaned


def authenticate_user(email, password, role):
    requested_role = _normalize_role(role)

    # Temporary login lock: allow only one shared credential for both roles.
    if (
        (email or "").strip().lower() == LOCKED_LOGIN_EMAIL
        and (password or "") == LOCKED_LOGIN_PASSWORD
        and requested_role in {"staff", "student", "admin"}
    ):
        user_id_map = {
            "staff": 1,
            "student": 2,
            "admin": 3,
        }
        return {
            "id": user_id_map[requested_role],
            "full_name": "Thiru",
            "email": LOCKED_LOGIN_EMAIL,
            "role": requested_role,
            "is_active": True,
        }

    db_role = "teacher" if requested_role == "staff" else requested_role

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, full_name, email, password_hash, role, is_active
                FROM users
                WHERE email = %s AND role = %s
                LIMIT 1
                """,
                (email, db_role),
            )
            user = cursor.fetchone()

            if not user or not user["is_active"]:
                return None

            if not check_password_hash(user["password_hash"], password):
                return None

            cursor.execute(
                "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s",
                (user["id"],),
            )
            user["role"] = _normalize_role(user.get("role"))
            return user
    finally:
        connection.close()


def login_user(user):
    session.clear()
    session["user"] = {
        "id": user["id"],
        "name": user["full_name"],
        "email": user["email"],
        "role": user["role"],
    }


def record_login_audit(user_id, ip_address=None, user_agent=None):
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO login_audit (user_id, ip_address, user_agent)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, ip_address, user_agent),
                )
        finally:
            connection.close()
    except MySQLError:
        return


def logout_user():
    session.clear()


def current_user():
    return session.get("user")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def teacher_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        if _normalize_role(user.get("role")) != "staff":
            flash("Staff access is required for that page.", "warning")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        if user.get("role") != "admin":
            flash("Admin access is required for that page.", "warning")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view


def staff_or_admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))

        role = _normalize_role(user.get("role"))
        if role not in {"staff", "admin"}:
            flash("Staff or admin access is required for that page.", "warning")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped_view
