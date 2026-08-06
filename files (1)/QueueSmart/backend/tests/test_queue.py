"""Tests for the Queue Management Module."""

import pytest

from app.modules import auth_module, queue_module, service_module
from app.validators import ConflictError, NotFoundError, ValidationError


@pytest.fixture
def user():
    return auth_module.get_user_by_token(
        auth_module.login_user({
            "email": "user@queuesmart.com", "password": "password123",
        })["token"]
    )


@pytest.fixture
def people(make_user):
    """Four extra registered users, returned as raw user records."""
    from app.store import store
    created = []
    for name in ("Alex", "Sam", "Jordan", "Taylor"):
        public, _ = make_user(first=name)
        created.append(store.users[public["id"]])
    return created


class TestJoinQueue:
    def test_first_person_gets_position_one(self, user):
        entry = queue_module.join_queue(user, 1)
        assert entry["position"] == 1
        assert entry["service_id"] == 1
        assert entry["user_name"] == "Demo User"

    def test_entry_inherits_service_priority(self, user):
        assert queue_module.join_queue(user, 3)["priority"] == "high"

    def test_explicit_priority_overrides_service_default(self, user):
        assert queue_module.join_queue(user, 1, {"priority": "high"})["priority"] == "high"

    def test_invalid_priority_rejected(self, user):
        with pytest.raises(ValidationError):
            queue_module.join_queue(user, 1, {"priority": "emergency"})

    def test_cannot_join_twice(self, user):
        queue_module.join_queue(user, 1)
        with pytest.raises(ConflictError) as exc:
            queue_module.join_queue(user, 1)
        assert "already in" in exc.value.message

    def test_can_be_in_two_different_queues(self, user):
        queue_module.join_queue(user, 1)
        assert queue_module.join_queue(user, 2)["position"] == 1

    def test_cannot_join_closed_service(self, user):
        service_module.set_open(1, False)
        with pytest.raises(ConflictError):
            queue_module.join_queue(user, 1)

    def test_cannot_join_unknown_service(self, user):
        with pytest.raises(NotFoundError):
            queue_module.join_queue(user, 404)

    def test_wait_estimate_included(self, user, people):
        queue_module.join_queue(people[0], 1)
        queue_module.join_queue(people[1], 1)
        entry = queue_module.join_queue(user, 1)
        assert entry["position"] == 3
        assert entry["estimated_wait_minutes"] == 30  # 2 ahead x 15 min
        assert entry["wait_label"] == "About 30 minutes"


class TestQueueOrdering:
    def test_same_priority_is_first_come_first_served(self, people):
        for person in people[:3]:
            queue_module.join_queue(person, 1)

        names = [e["user_name"] for e in queue_module.view_queue(1)["entries"]]
        assert names == [f"{p['first_name']} {p['last_name']}" for p in people[:3]]

    def test_high_priority_jumps_ahead_of_medium(self, people):
        queue_module.join_queue(people[0], 1)                        # medium
        queue_module.join_queue(people[1], 1)                        # medium
        queue_module.join_queue(people[2], 1, {"priority": "high"})  # high, joined last

        entries = queue_module.view_queue(1)["entries"]
        assert entries[0]["user_id"] == people[2]["id"]
        assert entries[0]["position"] == 1

    def test_low_priority_falls_behind(self, people):
        queue_module.join_queue(people[0], 1, {"priority": "low"})
        queue_module.join_queue(people[1], 1, {"priority": "medium"})

        entries = queue_module.view_queue(1)["entries"]
        assert entries[0]["user_id"] == people[1]["id"]

    def test_ties_within_priority_keep_arrival_order(self, people):
        queue_module.join_queue(people[0], 1, {"priority": "high"})
        queue_module.join_queue(people[1], 1, {"priority": "high"})

        entries = queue_module.view_queue(1)["entries"]
        assert [e["user_id"] for e in entries] == [people[0]["id"], people[1]["id"]]

    def test_positions_are_sequential(self, people):
        for person in people:
            queue_module.join_queue(person, 1)

        positions = [e["position"] for e in queue_module.view_queue(1)["entries"]]
        assert positions == [1, 2, 3, 4]

    def test_get_position_returns_none_when_absent(self, user):
        assert queue_module.get_position(1, user["id"]) is None


class TestLeaveQueue:
    def test_leaving_removes_the_user(self, user):
        queue_module.join_queue(user, 1)
        queue_module.leave_queue(user, 1)
        assert queue_module.get_position(1, user["id"]) is None

    def test_leaving_shifts_everyone_forward(self, user, people):
        queue_module.join_queue(people[0], 1)
        queue_module.join_queue(user, 1)
        queue_module.leave_queue(people[0], 1)
        assert queue_module.get_position(1, user["id"]) == 1

    def test_leaving_a_queue_you_are_not_in_raises(self, user):
        with pytest.raises(NotFoundError):
            queue_module.leave_queue(user, 1)

    def test_leaving_unknown_service_raises(self, user):
        with pytest.raises(NotFoundError):
            queue_module.leave_queue(user, 404)


class TestServeNext:
    def test_serves_the_front_of_the_queue(self, people):
        queue_module.join_queue(people[0], 1)
        queue_module.join_queue(people[1], 1)

        result = queue_module.serve_next(1)
        assert result["served"]["user_id"] == people[0]["id"]
        assert result["remaining"] == 1

    def test_respects_priority_order(self, people):
        queue_module.join_queue(people[0], 1)
        queue_module.join_queue(people[1], 1, {"priority": "high"})

        assert queue_module.serve_next(1)["served"]["user_id"] == people[1]["id"]

    def test_empty_queue_raises_conflict(self):
        with pytest.raises(ConflictError) as exc:
            queue_module.serve_next(1)
        assert "empty" in exc.value.message

    def test_unknown_service_raises(self):
        with pytest.raises(NotFoundError):
            queue_module.serve_next(404)

    def test_served_entry_records_actual_wait(self, people):
        queue_module.join_queue(people[0], 1)
        result = queue_module.serve_next(1)
        assert result["served"]["actual_wait_minutes"] is not None


class TestAdminRemoveAndMove:
    def test_admin_can_remove_an_entry(self, people):
        entry = queue_module.join_queue(people[0], 1)
        queue_module.remove_entry(1, entry["entry_id"])
        assert queue_module.view_queue(1)["queue_length"] == 0

    def test_removing_unknown_entry_raises(self):
        with pytest.raises(NotFoundError):
            queue_module.remove_entry(1, 999)

    def test_move_down_swaps_with_next(self, people):
        first = queue_module.join_queue(people[0], 1)
        queue_module.join_queue(people[1], 1)

        entries = queue_module.move_entry(1, first["entry_id"], "down")["entries"]
        assert entries[0]["user_id"] == people[1]["id"]
        assert entries[1]["user_id"] == people[0]["id"]

    def test_move_up_swaps_with_previous(self, people):
        queue_module.join_queue(people[0], 1)
        second = queue_module.join_queue(people[1], 1)

        entries = queue_module.move_entry(1, second["entry_id"], "up")["entries"]
        assert entries[0]["user_id"] == people[1]["id"]

    def test_cannot_move_past_the_top(self, people):
        first = queue_module.join_queue(people[0], 1)
        with pytest.raises(ConflictError):
            queue_module.move_entry(1, first["entry_id"], "up")

    def test_moving_unknown_entry_raises(self):
        with pytest.raises(NotFoundError):
            queue_module.move_entry(1, 999, "up")


class TestUserStatus:
    def test_reports_no_queues_when_idle(self, user):
        assert queue_module.user_status(user) == {"in_queue": False, "queues": []}

    def test_reports_every_active_queue(self, user):
        queue_module.join_queue(user, 1)
        queue_module.join_queue(user, 2)

        status = queue_module.user_status(user)
        assert status["in_queue"] is True
        assert len(status["queues"]) == 2

    def test_status_drops_deleted_services(self, user):
        queue_module.join_queue(user, 1)
        service_module.delete_service(1)
        assert queue_module.user_status(user)["in_queue"] is False


class TestQueueEndpoints:
    def test_join_requires_login(self, client):
        assert client.post("/api/services/1/queue/join").status_code == 401

    def test_join_returns_201_with_entry(self, client, auth):
        response = client.post("/api/services/1/queue/join", headers=auth)
        assert response.status_code == 201
        assert response.get_json()["entry"]["position"] == 1

    def test_duplicate_join_returns_409(self, client, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        assert client.post("/api/services/1/queue/join", headers=auth).status_code == 409

    def test_leave_returns_200(self, client, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        assert client.delete("/api/services/1/queue/leave", headers=auth).status_code == 200

    def test_status_endpoint(self, client, auth):
        client.post("/api/services/2/queue/join", headers=auth)
        data = client.get("/api/queue/status", headers=auth).get_json()
        assert data["in_queue"] is True
        assert data["queues"][0]["service_name"] == "Service 2"

    def test_view_queue_requires_admin(self, client, auth):
        assert client.get("/api/services/1/queue", headers=auth).status_code == 403

    def test_admin_can_view_queue(self, client, admin_auth, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        data = client.get("/api/services/1/queue", headers=admin_auth).get_json()
        assert data["queue_length"] == 1
        assert data["entries"][0]["position"] == 1

    def test_admin_can_serve_next(self, client, admin_auth, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        response = client.post("/api/services/1/queue/serve-next", headers=admin_auth)
        assert response.status_code == 200
        assert response.get_json()["remaining"] == 0

    def test_serve_next_on_empty_queue_returns_409(self, client, admin_auth):
        assert client.post(
            "/api/services/1/queue/serve-next", headers=admin_auth
        ).status_code == 409

    def test_admin_can_remove_entry(self, client, admin_auth, auth):
        entry = client.post("/api/services/1/queue/join", headers=auth).get_json()["entry"]
        response = client.delete(
            f"/api/services/1/queue/{entry['entry_id']}", headers=admin_auth
        )
        assert response.status_code == 200

    def test_move_requires_valid_direction(self, client, admin_auth, auth):
        entry = client.post("/api/services/1/queue/join", headers=auth).get_json()["entry"]
        response = client.patch(
            f"/api/services/1/queue/{entry['entry_id']}/move",
            json={"direction": "sideways"},
            headers=admin_auth,
        )
        assert response.status_code == 400
