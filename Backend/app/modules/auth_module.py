"""
Authentication Module.

Handles registration, login, password hashing, role assignment
(user vs administrator) and token-based session lookup.
"""

import hashlib
import secrets
from datetime import datetime, timezone

from app.store import store
from app.validators import (
    AuthError,
    ConflictError,
    MAX_NAME_LENGTH,
    ValidationError,
    VALID_ROLES,
    require_payload,
    validate_choice,
    validate_email,
    validate_password,
    validate_string,
)

# In a real deployment this would live in an environment variable.
ADMIN_KEY = "QUEUE-ADMIN-2026"


def _now():
    return datetime.now(timezone.utc).isoformat()


def hash_password(password, salt=None):
    """Salted SHA-256 hash. Stored as 'salt$digest'."""
    salt = salt or secrets.token_hex(8)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_password(password, stored_hash):
    try:
        salt, _ = stored_hash.split("$", 1)
    except (ValueError, AttributeError):
        return False
    return secrets.compare_digest(hash_password(password, salt), stored_hash)


def public_user(user):
 
    return {
        "id": user["id"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "full_name": f"{user['first_name']} {user['last_name']}",
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def validate_registration(data):

    data = require_payload(data)

    cleaned = {
        "first_name": validate_string(data, "first_name", "First name", MAX_NAME_LENGTH),
        "last_name": validate_string(data, "last_name", "Last name", MAX_NAME_LENGTH),
        "email": validate_email(data),
        "password": validate_password(data),
        "role": validate_choice(data, "role", "Role", VALID_ROLES, default="user"),
    }

    confirm = data.get("confirm_password")
    if confirm is not None and confirm != cleaned["password"]:
        raise ValidationError("confirm_password", "Passwords do not match.")

    if cleaned["role"] == "admin":
        admin_key = validate_string(data, "admin_key", "Admin key", 64)
        if admin_key != ADMIN_KEY:
            raise ValidationError("admin_key", "Admin key is not valid.")

    return cleaned


def register_user(data):
 
    cleaned = validate_registration(data)

    if store.find_user_by_email(cleaned["email"]):
        raise ConflictError("An account with that email already exists.")

    user = {
        "id": store.next_user_id(),
        "first_name": cleaned["first_name"],
        "last_name": cleaned["last_name"],
        "email": cleaned["email"],
        "password_hash": hash_password(cleaned["password"]),
        "role": cleaned["role"],
        "created_at": _now(),
    }

    store.users[user["id"]] = user

    return {"user": public_user(user), "token": create_session(user)}


def login_user(data):
    """Authenticate an existing account. Returns {user, token}."""
    data = require_payload(data)

    email = validate_email(data)
    password = validate_password(data)
    requested_role = validate_choice(data, "role", "Role", VALID_ROLES, default="user")

    user = store.find_user_by_email(email)

    if not user or not verify_password(password, user["password_hash"]):
        raise AuthError("Email or password is incorrect.")

    # The admin login form asks for the admin key as a second factor.
    if requested_role == "admin":
        admin_key = validate_string(data, "admin_key", "Admin key", 64)
        if admin_key != ADMIN_KEY or user["role"] != "admin":
            raise AuthError("Admin credentials are not valid.", status_code=403)

    return {"user": public_user(user), "token": create_session(user)}


def create_session(user):
    token = secrets.token_hex(16)
    store.sessions[token] = user["id"]
    return token


def get_user_by_token(token):
    if not token:
        raise AuthError("Authentication token is missing.")

    user_id = store.sessions.get(token)

    if user_id is None or user_id not in store.users:
        raise AuthError("Session is invalid or has expired.")

    return store.users[user_id]


def logout(token):
    store.sessions.pop(token, None)
    return {"message": "Logged out."}


def require_role(user, role):
    if user["role"] != role:
        raise AuthError(f"This action requires the {role} role.", status_code=403)
    return user
