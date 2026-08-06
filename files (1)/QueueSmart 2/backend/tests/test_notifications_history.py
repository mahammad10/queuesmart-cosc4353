"""Tests for the Notification Module and the History Module."""

import pytest

from app.modules import (
    auth_module,
    history_module,
    notification_module,
    queue_module,
    service_module,
)
from app.store import store


@pytest.fixture
def user():
    return auth_module.get_user_by_token(
        auth_module.login_user({
            "email": "user@queuesmart.com", "password": "password123",
        })["token"]
    )


@pytest.fixture
def people(make_user):
    created = []
    for name in ("Alex", "Sam", "Jordan", "Taylor"):
        public, _ = make_user(first=name)
        created.append(store.users[public["id"]])
    return created


def messages_for(user_id):
    return [n["message"] for n in notification_module.list_for_user(user_id)]


class TestNotificationTriggers:
    def test_joining_notifies_the_user(self, user):
        queue_module.join_queue(user, 1)
        assert any("You joined Service 1" in m for m in messages_for(user["id"]))

    def test_join_notification_includes_position_and_wait(self, user):
        queue_module.join_queue(user, 1)
        joined = [
            n for n in notification_module.list_for_user(user["id"])
            if n["type"] == "queue_joined"
        ][0]
        assert "number 1" in joined["message"]
        assert "estimated wait" in joined["message"]

    def test_front_of_queue_gets_almost_up_warning(self, user):
        queue_module.join_queue(user, 1)
        types = [n["type"] for n in notification_module.list_for_user(user["id"])]
        assert "almost_up" in types

    def test_far_back_user_is_not_warned(self, user, people):
        for person in people[:3]:
            queue_module.join_queue(person, 1)
        queue_module.join_queue(user, 1)  # position 4

        types = [n["type"] for n in notification_module.list_for_user(user["id"])]
        assert "almost_up" not in types

    def test_warning_fires_once_the_user_moves_up(self, user, people):
        for person in people[:3]:
            queue_module.join_queue(person, 1)
        queue_module.join_queue(user, 1)  # position 4

        queue_module.serve_next(1)  # user is now 3rd
        assert "almost_up" not in [
            n["type"] for n in notification_module.list_for_user(user["id"])
        ]

        queue_module.serve_next(1)  # user is now 2nd
        assert "almost_up" in [
            n["type"] for n in notification_module.list_for_user(user["id"])
        ]

    def test_warning_is_not_repeated(self, user, people):
        queue_module.join_queue(people[0], 1)
        queue_module.join_queue(user, 1)          # position 2, warned once
        queue_module.join_queue(people[1], 1)     # nothing changes for the user

        warnings = [
            n for n in notification_module.list_for_user(user["id"])
            if n["type"] == "almost_up"
        ]
        assert len(warnings) == 1

    def test_served_user_is_notified(self, user):
        queue_module.join_queue(user, 1)
        queue_module.serve_next(1)
        assert any("being served now" in m for m in messages_for(user["id"]))

    def test_leaving_is_notified(self, user):
        queue_module.join_queue(user, 1)
        queue_module.leave_queue(user, 1)
        assert any("You left" in m for m in messages_for(user["id"]))

    def test_admin_removal_is_notified(self, user):
        entry = queue_module.join_queue(user, 1)
        queue_module.remove_entry(1, entry["entry_id"])
        assert any("removed" in m for m in messages_for(user["id"]))


class TestNotificationStorage:
    def test_notifications_are_private_to_each_user(self, user, people):
        queue_module.join_queue(user, 1)
        assert messages_for(people[0]["id"]) == []

    def test_broadcasts_reach_everyone(self, user, people):
        notification_module.push(None, "System maintenance tonight.", "system")
        assert any("maintenance" in m for m in messages_for(user["id"]))
        assert any("maintenance" in m for m in messages_for(people[0]["id"]))

    def test_newest_notification_comes_first(self, user):
        notification_module.push(user["id"], "First message")
        notification_module.push(user["id"], "Second message")
        assert messages_for(user["id"])[0] == "Second message"

    def test_unknown_type_falls_back_to_system(self, user):
        assert notification_module.push(user["id"], "hi", "not-a-type")["type"] == "system"

    def test_unread_filter(self, user):
        notification_module.push(user["id"], "Unread one")
        unread = notification_module.list_for_user(user["id"], unread_only=True)
        assert len(unread) == 1

    def test_mark_all_read(self, user):
        notification_module.push(user["id"], "One")
        notification_module.push(user["id"], "Two")
        assert notification_module.mark_all_read(user["id"])["marked_read"] == 2
        assert notification_module.list_for_user(user["id"], unread_only=True) == []

    def test_limit_is_respected(self, user):
        for i in range(30):
            notification_module.push(user["id"], f"Message {i}")
        assert len(notification_module.list_for_user(user["id"], limit=5)) == 5


class TestHistory:
    def test_joining_opens_a_waiting_record(self, user):
        queue_module.join_queue(user, 1)
        records = history_module.list_for_user(user["id"])
        assert len(records) == 1
        assert records[0]["status"] == "waiting"
        assert records[0]["service_name"] == "Service 1"
        assert records[0]["ended_at"] is None

    def test_being_served_closes_the_record(self, user):
        queue_module.join_queue(user, 1)
        queue_module.serve_next(1)
        record = history_module.list_for_user(user["id"])[0]
        assert record["status"] == "served"
        assert record["ended_at"] is not None
        assert record["actual_wait_minutes"] >= 0

    def test_leaving_closes_the_record_as_left(self, user):
        queue_module.join_queue(user, 1)
        queue_module.leave_queue(user, 1)
        assert history_module.list_for_user(user["id"])[0]["status"] == "left"

    def test_admin_removal_closes_the_record_as_removed(self, user):
        entry = queue_module.join_queue(user, 1)
        queue_module.remove_entry(1, entry["entry_id"])
        assert history_module.list_for_user(user["id"])[0]["status"] == "removed"

    def test_repeat_visits_create_separate_records(self, user):
        queue_module.join_queue(user, 1)
        queue_module.leave_queue(user, 1)
        queue_module.join_queue(user, 1)
        assert len(history_module.list_for_user(user["id"])) == 2

    def test_status_filter(self, user):
        queue_module.join_queue(user, 1)
        queue_module.leave_queue(user, 1)
        queue_module.join_queue(user, 2)
        assert len(history_module.list_for_user(user["id"], status="left")) == 1

    def test_closing_without_an_open_record_returns_none(self, user):
        assert history_module.close_record(user["id"], 1, "served") is None

    def test_service_history_lists_every_participant(self, user, people):
        queue_module.join_queue(user, 1)
        queue_module.join_queue(people[0], 1)
        assert len(history_module.list_for_service(1)) == 2

    def test_summary_counts_outcomes(self, user):
        queue_module.join_queue(user, 1)
        queue_module.serve_next(1)
        queue_module.join_queue(user, 2)
        queue_module.leave_queue(user, 2)

        summary = history_module.summary_for_user(user["id"])
        assert summary["total_visits"] == 2
        assert summary["served"] == 1
        assert summary["left"] == 1

    def test_summary_is_zeroed_for_new_users(self, people):
        assert history_module.summary_for_user(people[0]["id"])["total_visits"] == 0


class TestNotificationAndHistoryEndpoints:
    def test_notifications_require_login(self, client):
        assert client.get("/api/notifications").status_code == 401

    def test_notifications_endpoint_returns_items(self, client, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        data = client.get("/api/notifications", headers=auth).get_json()
        assert data["unread_count"] >= 1
        assert len(data["notifications"]) >= 1

    def test_unread_query_parameter(self, client, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        client.post("/api/notifications/read", headers=auth)
        data = client.get("/api/notifications?unread=true", headers=auth).get_json()
        assert data["notifications"] == []

    def test_history_endpoint_returns_records_and_summary(self, client, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        data = client.get("/api/history", headers=auth).get_json()
        assert len(data["history"]) == 1
        assert data["summary"]["total_visits"] == 1

    def test_service_history_requires_admin(self, client, auth):
        assert client.get("/api/history/service/1", headers=auth).status_code == 403

    def test_admin_can_read_service_history(self, client, admin_auth, auth):
        client.post("/api/services/1/queue/join", headers=auth)
        data = client.get("/api/history/service/1", headers=admin_auth).get_json()
        assert len(data["history"]) == 1


class TestStoreReset:
    def test_reset_restores_seed_data(self, user):
        queue_module.join_queue(user, 1)
        service_module.delete_service(2)

        store.reset()

        assert len(store.services) == 3
        assert store.history == []
        assert store.notifications == []
        assert store.get_queue(1) == []
