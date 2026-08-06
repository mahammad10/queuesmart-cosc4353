"""Tests for the Authentication Module."""

import pytest

from app.modules import auth_module
from app.validators import AuthError, ConflictError, ValidationError


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = auth_module.hash_password("password123")
        assert "password123" not in hashed
        assert "$" in hashed

    def test_same_password_gets_different_salt(self):
        assert auth_module.hash_password("password123") != auth_module.hash_password("password123")

    def test_verify_accepts_correct_password(self):
        hashed = auth_module.hash_password("password123")
        assert auth_module.verify_password("password123", hashed) is True

    def test_verify_rejects_wrong_password(self):
        hashed = auth_module.hash_password("password123")
        assert auth_module.verify_password("wrongpassword", hashed) is False

    def test_verify_handles_malformed_hash(self):
        assert auth_module.verify_password("password123", "garbage") is False


class TestRegistration:
    def test_registers_a_user_and_returns_token(self):
        result = auth_module.register_user({
            "first_name": "Imad",
            "last_name": "Student",
            "email": "imad@uh.edu",
            "password": "password123",
            "confirm_password": "password123",
        })
        assert result["user"]["role"] == "user"
        assert result["user"]["email"] == "imad@uh.edu"
        assert len(result["token"]) > 10

    def test_password_hash_is_never_returned(self):
        result = auth_module.register_user({
            "first_name": "Imad", "last_name": "Student",
            "email": "safe@uh.edu", "password": "password123",
        })
        assert "password_hash" not in result["user"]
        assert "password" not in result["user"]

    def test_duplicate_email_rejected(self):
        with pytest.raises(ConflictError):
            auth_module.register_user({
                "first_name": "Copy", "last_name": "Cat",
                "email": "user@queuesmart.com", "password": "password123",
            })

    def test_mismatched_confirmation_rejected(self):
        with pytest.raises(ValidationError) as exc:
            auth_module.register_user({
                "first_name": "A", "last_name": "B", "email": "mm@uh.edu",
                "password": "password123", "confirm_password": "different1",
            })
        assert exc.value.field == "confirm_password"

    def test_missing_first_name_rejected(self):
        with pytest.raises(ValidationError) as exc:
            auth_module.register_user({
                "last_name": "B", "email": "nf@uh.edu", "password": "password123",
            })
        assert exc.value.field == "first_name"

    def test_admin_registration_requires_correct_key(self):
        with pytest.raises(ValidationError) as exc:
            auth_module.register_user({
                "first_name": "Fake", "last_name": "Admin", "email": "fake@uh.edu",
                "password": "password123", "role": "admin", "admin_key": "wrong",
            })
        assert exc.value.field == "admin_key"

    def test_admin_registration_with_correct_key(self):
        result = auth_module.register_user({
            "first_name": "Real", "last_name": "Admin", "email": "real@uh.edu",
            "password": "password123", "role": "admin",
            "admin_key": auth_module.ADMIN_KEY,
        })
        assert result["user"]["role"] == "admin"

    def test_unknown_role_rejected(self):
        with pytest.raises(ValidationError):
            auth_module.register_user({
                "first_name": "X", "last_name": "Y", "email": "x@uh.edu",
                "password": "password123", "role": "superuser",
            })


class TestLogin:
    def test_valid_credentials_return_token(self):
        result = auth_module.login_user({
            "email": "user@queuesmart.com", "password": "password123",
        })
        assert result["user"]["email"] == "user@queuesmart.com"
        assert result["token"]

    def test_email_is_case_insensitive(self):
        result = auth_module.login_user({
            "email": "USER@QUEUESMART.COM", "password": "password123",
        })
        assert result["user"]["id"] == 1

    def test_wrong_password_rejected(self):
        with pytest.raises(AuthError):
            auth_module.login_user({
                "email": "user@queuesmart.com", "password": "wrongpassword",
            })

    def test_unknown_email_rejected(self):
        with pytest.raises(AuthError):
            auth_module.login_user({
                "email": "nobody@queuesmart.com", "password": "password123",
            })

    def test_admin_login_requires_admin_key(self):
        with pytest.raises(ValidationError):
            auth_module.login_user({
                "email": "admin@queuesmart.com", "password": "password123",
                "role": "admin",
            })

    def test_regular_user_cannot_log_in_as_admin(self):
        with pytest.raises(AuthError) as exc:
            auth_module.login_user({
                "email": "user@queuesmart.com", "password": "password123",
                "role": "admin", "admin_key": auth_module.ADMIN_KEY,
            })
        assert exc.value.status_code == 403


class TestSessions:
    def test_token_resolves_to_user(self, user_token):
        user = auth_module.get_user_by_token(user_token)
        assert user["email"] == "user@queuesmart.com"

    def test_missing_token_rejected(self):
        with pytest.raises(AuthError):
            auth_module.get_user_by_token(None)

    def test_invalid_token_rejected(self):
        with pytest.raises(AuthError):
            auth_module.get_user_by_token("not-a-real-token")

    def test_logout_invalidates_token(self, user_token):
        auth_module.logout(user_token)
        with pytest.raises(AuthError):
            auth_module.get_user_by_token(user_token)

    def test_require_role_blocks_wrong_role(self):
        user = auth_module.get_user_by_token(
            auth_module.login_user({
                "email": "user@queuesmart.com", "password": "password123",
            })["token"]
        )
        with pytest.raises(AuthError):
            auth_module.require_role(user, "admin")


class TestAuthEndpoints:
    def test_register_endpoint_returns_201(self, client):
        response = client.post("/api/auth/register", json={
            "first_name": "Api", "last_name": "User",
            "email": "api@uh.edu", "password": "password123",
        })
        assert response.status_code == 201
        assert response.get_json()["user"]["email"] == "api@uh.edu"

    def test_register_endpoint_validation_returns_400(self, client):
        response = client.post("/api/auth/register", json={
            "first_name": "Api", "last_name": "User",
            "email": "bad-email", "password": "password123",
        })
        assert response.status_code == 400
        assert response.get_json()["field"] == "email"

    def test_login_endpoint_returns_token(self, client):
        response = client.post("/api/auth/login", json={
            "email": "user@queuesmart.com", "password": "password123",
        })
        assert response.status_code == 200
        assert "token" in response.get_json()

    def test_login_endpoint_bad_credentials_returns_401(self, client):
        response = client.post("/api/auth/login", json={
            "email": "user@queuesmart.com", "password": "nopenopenope",
        })
        assert response.status_code == 401

    def test_me_endpoint_requires_token(self, client):
        assert client.get("/api/auth/me").status_code == 401

    def test_me_endpoint_with_token(self, client, auth):
        response = client.get("/api/auth/me", headers=auth)
        assert response.status_code == 200
        assert response.get_json()["user"]["role"] == "user"

    def test_logout_endpoint(self, client, auth):
        assert client.post("/api/auth/logout", headers=auth).status_code == 200
        assert client.get("/api/auth/me", headers=auth).status_code == 401

    def test_health_endpoint(self, client):
        assert client.get("/api/health").get_json()["status"] == "ok"

    def test_unknown_endpoint_returns_json_404(self, client):
        response = client.get("/api/does-not-exist")
        assert response.status_code == 404
        assert response.get_json()["error"] == "Not found"
