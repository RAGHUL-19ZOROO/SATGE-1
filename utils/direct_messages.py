import json
from datetime import datetime
from pathlib import Path


DATA_PATH = Path("data/direct_messages.json")


def _load_messages():
    if not DATA_PATH.exists():
        return []

    with DATA_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        return []
    return data


def _save_messages(messages):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(messages, file, indent=2)


def _normalize_role(role):
    cleaned = (role or "").strip().lower()
    return "staff" if cleaned == "teacher" else cleaned


def _default_contacts_for_role(role):
    normalized = _normalize_role(role)
    if normalized == "staff":
        return [
            {"id": 2, "name": "Student", "role": "student"},
        ]
    if normalized == "student":
        return [
            {"id": 1, "name": "Staff", "role": "staff"},
        ]
    if normalized == "admin":
        return [
            {"id": 1, "name": "Staff", "role": "staff"},
            {"id": 2, "name": "Student", "role": "student"},
        ]
    return []


def _is_contact_allowed(sender_role, receiver_role):
    sender = _normalize_role(sender_role)
    receiver = _normalize_role(receiver_role)

    if sender == "staff":
        return receiver == "student"
    if sender == "student":
        return receiver == "staff"
    if sender == "admin":
        return receiver in {"staff", "student", "admin"}
    return False


def list_dm_contacts(current_user):
    user_id = int(current_user.get("id"))
    user_role = _normalize_role(current_user.get("role"))

    contacts = {}
    for item in _default_contacts_for_role(user_role):
        if int(item["id"]) == user_id:
            continue
        contacts[int(item["id"])] = {
            "id": int(item["id"]),
            "name": item["name"],
            "role": _normalize_role(item["role"]),
        }

    for message in _load_messages():
        sender_id = int(message.get("sender_id", 0) or 0)
        receiver_id = int(message.get("receiver_id", 0) or 0)

        if sender_id == user_id:
            contacts[receiver_id] = {
                "id": receiver_id,
                "name": message.get("receiver_name") or "User",
                "role": _normalize_role(message.get("receiver_role")),
            }
        elif receiver_id == user_id:
            contacts[sender_id] = {
                "id": sender_id,
                "name": message.get("sender_name") or "User",
                "role": _normalize_role(message.get("sender_role")),
            }

    ordered = sorted(contacts.values(), key=lambda item: (item["role"], item["name"].lower()))
    if user_role in {"staff", "student"}:
        ordered = [item for item in ordered if _is_contact_allowed(user_role, item.get("role"))]
    return ordered


def get_thread(current_user, contact_id):
    user_id = int(current_user.get("id"))
    target_id = int(contact_id)

    thread = []
    for message in _load_messages():
        sender_id = int(message.get("sender_id", 0) or 0)
        receiver_id = int(message.get("receiver_id", 0) or 0)
        pair_matches = (
            (sender_id == user_id and receiver_id == target_id)
            or (sender_id == target_id and receiver_id == user_id)
        )
        if pair_matches:
            thread.append(message)

    return sorted(thread, key=lambda item: item.get("created_at", ""))


def send_message(current_user, contact, text):
    message_text = (text or "").strip()
    if not message_text:
        raise ValueError("Message is required.")
    if len(message_text) > 2000:
        raise ValueError("Message is too long. Keep it under 2,000 characters.")

    sender_role = _normalize_role(current_user.get("role"))
    receiver_role = _normalize_role(contact.get("role"))

    if int(current_user.get("id")) == int(contact.get("id")):
        raise ValueError("You cannot message yourself.")

    if not _is_contact_allowed(sender_role, receiver_role):
        raise ValueError("You can only message the allowed role for your account.")

    messages = _load_messages()
    payload = {
        "sender_id": int(current_user.get("id")),
        "sender_name": current_user.get("name") or "User",
        "sender_role": sender_role,
        "receiver_id": int(contact.get("id")),
        "receiver_name": contact.get("name") or "User",
        "receiver_role": receiver_role,
        "message": message_text,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    messages.append(payload)
    _save_messages(messages)
    return payload
