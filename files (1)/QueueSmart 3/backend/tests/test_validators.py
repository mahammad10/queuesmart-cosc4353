"""Unit tests for the shared validation layer."""

import pytest

from app.validators import (
    ValidationError,
    require_payload,
    validate_boolean,
    validate_choice,
    validate_email,
    validate_integer,
    validate_password,
    validate_string,
)


class TestRequirePayload:
    def test_accepts_dict(self):
        assert require_payload({"a": 1}) == {"a": 1}

    @pytest.mark.parametrize("bad", [None, "text", 12, ["list"]])
    def test_rejects_non_object(self, bad):
        with pytest.raises(ValidationError) as exc:
            require_payload(bad)
        assert exc.value.field == "body"


class TestValidateString:
    def test_trims_whitespace(self):
        assert validate_string({"name": "  Imad  "}, "name", "Name", 50) == "Imad"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError) as exc:
            validate_string({}, "name", "Name", 50)
        assert "required" in exc.value.message

    def test_blank_string_counts_as_missing(self):
        with pytest.raises(ValidationError):
            validate_string({"name": "   "}, "name", "Name", 50)

    def test_optional_field_returns_empty(self):
        assert validate_string({}, "note", "Note", 50, required=False) == ""

    def test_length_limit_enforced(self):
        with pytest.raises(ValidationError) as exc:
            validate_string({"name": "x" * 51}, "name", "Name", 50)
        assert "50 characters or fewer" in exc.value.message

    def test_min_length_enforced(self):
        with pytest.raises(ValidationError):
            validate_string({"name": "a"}, "name", "Name", 50, min_length=2)

    def test_wrong_type_rejected(self):
        with pytest.raises(ValidationError) as exc:
            validate_string({"name": 123}, "name", "Name", 50)
        assert "must be text" in exc.value.message


class TestValidateInteger:
    def test_accepts_int(self):
        assert validate_integer({"n": 15}, "n", "Duration") == 15

    def test_accepts_numeric_string(self):
        assert validate_integer({"n": " 20 "}, "n", "Duration") == 20

    def test_rejects_non_numeric(self):
        with pytest.raises(ValidationError) as exc:
            validate_integer({"n": "abc"}, "n", "Duration")
        assert "whole number" in exc.value.message

    def test_rejects_boolean(self):
        with pytest.raises(ValidationError):
            validate_integer({"n": True}, "n", "Duration")

    def test_enforces_minimum(self):
        with pytest.raises(ValidationError) as exc:
            validate_integer({"n": 0}, "n", "Duration", minimum=1)
        assert "at least 1" in exc.value.message

    def test_enforces_maximum(self):
        with pytest.raises(ValidationError):
            validate_integer({"n": 900}, "n", "Duration", maximum=480)

    def test_required_missing_raises(self):
        with pytest.raises(ValidationError):
            validate_integer({}, "n", "Duration")

    def test_optional_missing_returns_none(self):
        assert validate_integer({}, "n", "Duration", required=False) is None


class TestValidateChoice:
    def test_accepts_valid_choice_case_insensitive(self):
        assert validate_choice({"p": "HIGH"}, "p", "Priority", ("low", "high")) == "high"

    def test_rejects_invalid_choice(self):
        with pytest.raises(ValidationError) as exc:
            validate_choice({"p": "urgent"}, "p", "Priority", ("low", "high"))
        assert "must be one of" in exc.value.message

    def test_falls_back_to_default(self):
        assert validate_choice({}, "p", "Priority", ("low", "high"), default="low") == "low"

    def test_required_without_default_raises(self):
        with pytest.raises(ValidationError):
            validate_choice({}, "p", "Priority", ("low", "high"))


class TestValidateBoolean:
    @pytest.mark.parametrize("value,expected", [
        (True, True), (False, False), ("true", True), ("False", False),
    ])
    def test_accepts_booleans_and_strings(self, value, expected):
        assert validate_boolean({"b": value}, "b", "Flag") is expected

    def test_rejects_other_values(self):
        with pytest.raises(ValidationError):
            validate_boolean({"b": "maybe"}, "b", "Flag")

    def test_uses_default_when_absent(self):
        assert validate_boolean({}, "b", "Flag", default=True) is True


class TestValidateEmail:
    @pytest.mark.parametrize("email", [
        "imad@uh.edu", "a.b+tag@sub.domain.org", "TEST@EXAMPLE.COM",
    ])
    def test_accepts_valid_emails(self, email):
        assert validate_email({"email": email}) == email.lower()

    @pytest.mark.parametrize("email", [
        "no-at-sign", "missing@domain", "spaces in@mail.com", "@nolocal.com",
    ])
    def test_rejects_invalid_emails(self, email):
        with pytest.raises(ValidationError):
            validate_email({"email": email})


class TestValidatePassword:
    def test_accepts_long_enough_password(self):
        assert validate_password({"password": "password123"}) == "password123"

    def test_rejects_short_password(self):
        with pytest.raises(ValidationError) as exc:
            validate_password({"password": "short"})
        assert "at least 8" in exc.value.message

    def test_rejects_missing_password(self):
        with pytest.raises(ValidationError):
            validate_password({})

    def test_rejects_overlong_password(self):
        with pytest.raises(ValidationError):
            validate_password({"password": "x" * 129})
