"""Shared helpers for the route layer."""

from functools import wraps

from flask import g, request

from app.modules import auth_module
from app.validators import AuthError


def _token_from_request():
    header = request.headers.get("Authorization", "")

    if header.lower().startswith("bearer "):
        return header[7:].strip()

    return request.headers.get("X-Auth-Token", "").strip() or None


def login_required(view):
    """Attach the signed-in user to flask.g, or return 401."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = auth_module.get_user_by_token(_token_from_request())
        return view(*args, **kwargs)

    return wrapper


def admin_required(view):
    """Same as login_required, plus a role check that returns 403."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        user = auth_module.get_user_by_token(_token_from_request())

        if user["role"] != "admin":
            raise AuthError("Administrator access is required.", status_code=403)

        g.current_user = user
        return view(*args, **kwargs)

    return wrapper
