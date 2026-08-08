

import re

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")

VALID_PRIORITIES = ("low", "medium", "high")
VALID_ROLES = ("user", "admin")

MIN_PASSWORD_LENGTH = 8
MAX_NAME_LENGTH = 50
MAX_EMAIL_LENGTH = 120
MAX_SERVICE_NAME_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 500
MIN_DURATION = 1
MAX_DURATION = 480  # 8 hours is a sane upper bound for one appointment


class ValidationError(Exception):


    status_code = 400

    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message

    def to_dict(self):
        return {
            "error": "Validation failed",
            "field": self.field,
            "message": self.message,
        }


class NotFoundError(Exception):


    status_code = 404

    def __init__(self, message="Resource not found"):
        super().__init__(message)
        self.message = message

    def to_dict(self):
        return {"error": "Not found", "message": self.message}


class ConflictError(Exception):
  

    status_code = 409

    def __init__(self, message="Request conflicts with current state"):
        super().__init__(message)
        self.message = message

    def to_dict(self):
        return {"error": "Conflict", "message": self.message}


class AuthError(Exception):
    """Raised for bad credentials or missing / insufficient permissions."""

    def __init__(self, message="Not authorized", status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def to_dict(self):
        return {"error": "Unauthorized", "message": self.message}


# ----------------------------------------------------------------------
# Generic field validators
# ----------------------------------------------------------------------

def require_payload(data):
    """The request body must be a JSON object."""
    if data is None or not isinstance(data, dict):
        raise ValidationError("body", "Request body must be a JSON object.")
    return data


def validate_string(data, field, label, max_length, required=True, min_length=1):
    """Validate a required/optional string field and return it trimmed."""
    value = data.get(field)

    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise ValidationError(field, f"{label} is required.")
        return ""

    if not isinstance(value, str):
        raise ValidationError(field, f"{label} must be text.")

    value = value.strip()

    if len(value) < min_length:
        raise ValidationError(
            field, f"{label} must be at least {min_length} characters."
        )

    if len(value) > max_length:
        raise ValidationError(
            field, f"{label} must be {max_length} characters or fewer."
        )

    return value


def validate_integer(data, field, label, minimum=None, maximum=None, required=True):
    """Validate an integer field. Numeric strings like "15" are accepted."""
    value = data.get(field)

    if value is None or value == "":
        if required:
            raise ValidationError(field, f"{label} is required.")
        return None

    if isinstance(value, bool):
        raise ValidationError(field, f"{label} must be a whole number.")

    if isinstance(value, str):
        value = value.strip()

    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(field, f"{label} must be a whole number.")

    if minimum is not None and number < minimum:
        raise ValidationError(field, f"{label} must be at least {minimum}.")

    if maximum is not None and number > maximum:
        raise ValidationError(field, f"{label} must be {maximum} or less.")

    return number


def validate_choice(data, field, label, choices, required=True, default=None):
    """Validate that a value is one of an allowed set (case-insensitive)."""
    value = data.get(field)

    if value is None or value == "":
        if required and default is None:
            raise ValidationError(field, f"{label} is required.")
        return default

    if not isinstance(value, str):
        raise ValidationError(field, f"{label} must be text.")

    value = value.strip().lower()

    if value not in choices:
        allowed = ", ".join(choices)
        raise ValidationError(field, f"{label} must be one of: {allowed}.")

    return value


def validate_boolean(data, field, label, default=None):
    value = data.get(field)

    if value is None:
        if default is None:
            raise ValidationError(field, f"{label} is required.")
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str) and value.strip().lower() in ("true", "false"):
        return value.strip().lower() == "true"

    raise ValidationError(field, f"{label} must be true or false.")


# ----------------------------------------------------------------------
# Domain-specific validators
# ----------------------------------------------------------------------

def validate_email(data, field="email"):
    email = validate_string(data, field, "Email", MAX_EMAIL_LENGTH)

    if not EMAIL_PATTERN.match(email):
        raise ValidationError(field, "Please enter a valid email address.")

    return email.lower()


def validate_password(data, field="password"):
    value = data.get(field)

    if not value or not isinstance(value, str):
        raise ValidationError(field, "Password is required.")

    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            field, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )

    if len(value) > 128:
        raise ValidationError(field, "Password must be 128 characters or fewer.")

    return value
