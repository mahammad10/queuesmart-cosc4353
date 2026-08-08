

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app                      # noqa: E402
from app.modules import auth_module             # noqa: E402
from app.store import store                     # noqa: E402


@pytest.fixture(autouse=True)
def clean_store():
    """Every test starts from the same seeded state."""
    store.reset()
    yield
    store.reset()


@pytest.fixture
def app():
    return create_app(testing=True)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_token():
    result = auth_module.login_user({
        "email": "user@queuesmart.com",
        "password": "password123",
    })
    return result["token"]


@pytest.fixture
def admin_token():
    result = auth_module.login_user({
        "email": "admin@queuesmart.com",
        "password": "password123",
        "role": "admin",
        "admin_key": auth_module.ADMIN_KEY,
    })
    return result["token"]


@pytest.fixture
def auth(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def make_user():
    """Factory that registers extra users on demand."""
    counter = {"n": 0}

    def _make(first="Test", last="Person"):
        counter["n"] += 1
        result = auth_module.register_user({
            "first_name": first,
            "last_name": f"{last}{counter['n']}",
            "email": f"person{counter['n']}@queuesmart.com",
            "password": "password123",
        })
        return result["user"], result["token"]

    return _make
