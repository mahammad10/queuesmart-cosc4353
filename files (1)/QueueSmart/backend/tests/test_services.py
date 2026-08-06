"""Tests for the Service Management Module."""

import pytest

from app.modules import service_module
from app.validators import ConflictError, NotFoundError, ValidationError


VALID = {
    "name": "Passport Renewal",
    "description": "Renew an existing passport.",
    "expected_duration": 20,
    "priority": "high",
}


class TestCreateService:
    def test_creates_with_all_fields(self):
        service = service_module.create_service(VALID)
        assert service["name"] == "Passport Renewal"
        assert service["expected_duration"] == 20
        assert service["priority"] == "high"
        assert service["is_open"] is True
        assert service["queue_length"] == 0

    def test_priority_defaults_to_medium(self):
        payload = dict(VALID)
        payload.pop("priority")
        assert service_module.create_service(payload)["priority"] == "medium"

    def test_ids_increment(self):
        first = service_module.create_service(VALID)
        second = service_module.create_service(dict(VALID, name="Another Service"))
        assert second["id"] == first["id"] + 1

    def test_duplicate_name_rejected(self):
        service_module.create_service(VALID)
        with pytest.raises(ConflictError):
            service_module.create_service(dict(VALID, name="passport renewal"))

    def test_missing_name_rejected(self):
        payload = dict(VALID)
        payload.pop("name")
        with pytest.raises(ValidationError) as exc:
            service_module.create_service(payload)
        assert exc.value.field == "name"

    def test_name_over_100_chars_rejected(self):
        with pytest.raises(ValidationError):
            service_module.create_service(dict(VALID, name="x" * 101))

    def test_missing_description_rejected(self):
        payload = dict(VALID)
        payload.pop("description")
        with pytest.raises(ValidationError) as exc:
            service_module.create_service(payload)
        assert exc.value.field == "description"

    def test_zero_duration_rejected(self):
        with pytest.raises(ValidationError):
            service_module.create_service(dict(VALID, expected_duration=0))

    def test_non_numeric_duration_rejected(self):
        with pytest.raises(ValidationError) as exc:
            service_module.create_service(dict(VALID, expected_duration="twenty"))
        assert exc.value.field == "expected_duration"

    def test_duration_over_limit_rejected(self):
        with pytest.raises(ValidationError):
            service_module.create_service(dict(VALID, expected_duration=1000))

    def test_invalid_priority_rejected(self):
        with pytest.raises(ValidationError):
            service_module.create_service(dict(VALID, priority="urgent"))

    def test_numeric_duration_string_accepted(self):
        assert service_module.create_service(
            dict(VALID, expected_duration="25")
        )["expected_duration"] == 25


class TestListAndGet:
    def test_seed_services_exist(self):
        assert len(service_module.list_services()) == 3

    def test_list_sorted_by_id(self):
        ids = [s["id"] for s in service_module.list_services()]
        assert ids == sorted(ids)

    def test_only_open_filter(self):
        service_module.set_open(1, False)
        open_ids = [s["id"] for s in service_module.list_services(only_open=True)]
        assert 1 not in open_ids and len(open_ids) == 2

    def test_get_unknown_service_raises(self):
        with pytest.raises(NotFoundError):
            service_module.get_service(9999)


class TestUpdateService:
    def test_updates_single_field(self):
        updated = service_module.update_service(1, {"expected_duration": 45})
        assert updated["expected_duration"] == 45
        assert updated["name"] == "Service 1"

    def test_updates_multiple_fields(self):
        updated = service_module.update_service(1, {
            "name": "Renamed", "priority": "high",
        })
        assert updated["name"] == "Renamed"
        assert updated["priority"] == "high"

    def test_invalid_update_rejected(self):
        with pytest.raises(ValidationError):
            service_module.update_service(1, {"expected_duration": -5})

    def test_renaming_onto_existing_name_rejected(self):
        with pytest.raises(ConflictError):
            service_module.update_service(1, {"name": "Service 2"})

    def test_keeping_own_name_allowed(self):
        assert service_module.update_service(1, {"name": "Service 1"})["name"] == "Service 1"

    def test_update_unknown_service_raises(self):
        with pytest.raises(NotFoundError):
            service_module.update_service(404, {"name": "Ghost Service"})


class TestOpenCloseAndDelete:
    def test_close_and_reopen(self):
        assert service_module.set_open(1, False)["is_open"] is False
        assert service_module.set_open(1, True)["is_open"] is True

    def test_delete_removes_service_and_queue(self):
        from app.store import store
        service_module.delete_service(1)
        assert 1 not in store.services
        assert 1 not in store.queues

    def test_delete_unknown_service_raises(self):
        with pytest.raises(NotFoundError):
            service_module.delete_service(404)


class TestServiceEndpoints:
    def test_list_is_public(self, client):
        response = client.get("/api/services")
        assert response.status_code == 200
        assert len(response.get_json()["services"]) == 3

    def test_get_single_service(self, client):
        assert client.get("/api/services/1").get_json()["service"]["id"] == 1

    def test_get_unknown_service_returns_404(self, client):
        assert client.get("/api/services/404").status_code == 404

    def test_create_requires_admin(self, client, auth):
        assert client.post("/api/services", json=VALID, headers=auth).status_code == 403

    def test_create_requires_login(self, client):
        assert client.post("/api/services", json=VALID).status_code == 401

    def test_admin_can_create(self, client, admin_auth):
        response = client.post("/api/services", json=VALID, headers=admin_auth)
        assert response.status_code == 201
        assert response.get_json()["service"]["name"] == "Passport Renewal"

    def test_admin_create_validation_returns_400(self, client, admin_auth):
        response = client.post(
            "/api/services", json=dict(VALID, expected_duration=0), headers=admin_auth
        )
        assert response.status_code == 400

    def test_admin_can_update(self, client, admin_auth):
        response = client.put(
            "/api/services/1", json={"description": "Updated text."}, headers=admin_auth
        )
        assert response.get_json()["service"]["description"] == "Updated text."

    def test_admin_can_toggle_status(self, client, admin_auth):
        response = client.patch(
            "/api/services/1/status", json={"is_open": False}, headers=admin_auth
        )
        assert response.get_json()["service"]["is_open"] is False

    def test_admin_can_delete(self, client, admin_auth):
        assert client.delete("/api/services/3", headers=admin_auth).status_code == 200
        assert len(client.get("/api/services").get_json()["services"]) == 2
