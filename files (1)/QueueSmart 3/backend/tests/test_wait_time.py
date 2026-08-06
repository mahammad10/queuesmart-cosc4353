"""Tests for the Wait-Time Estimation logic."""

import pytest

from app.modules.wait_time import (
    ALMOST_UP_THRESHOLD,
    describe_wait,
    estimate_queue_drain,
    estimate_wait_minutes,
    is_almost_up,
    priority_weight,
)
from app.validators import ValidationError


class TestPriorityWeight:
    def test_high_beats_medium_beats_low(self):
        assert priority_weight("high") > priority_weight("medium") > priority_weight("low")

    def test_case_insensitive(self):
        assert priority_weight("HIGH") == priority_weight("high")

    def test_unknown_priority_defaults_to_medium(self):
        assert priority_weight("bogus") == priority_weight("medium")


class TestEstimateWaitMinutes:
    def test_front_of_queue_waits_zero(self):
        assert estimate_wait_minutes(1, 15) == 0

    def test_wait_scales_with_position(self):
        assert estimate_wait_minutes(2, 15) == 15
        assert estimate_wait_minutes(4, 15) == 45

    def test_wait_scales_with_duration(self):
        assert estimate_wait_minutes(3, 10) == 20
        assert estimate_wait_minutes(3, 30) == 60

    def test_high_priority_shortens_estimate(self):
        assert estimate_wait_minutes(3, 20, "high") < estimate_wait_minutes(3, 20, "medium")

    def test_low_priority_lengthens_estimate(self):
        assert estimate_wait_minutes(3, 20, "low") > estimate_wait_minutes(3, 20, "medium")

    def test_result_is_a_whole_number(self):
        assert isinstance(estimate_wait_minutes(4, 7, "high"), int)

    @pytest.mark.parametrize("position", [0, -3, "2", 1.5, True])
    def test_invalid_position_rejected(self, position):
        with pytest.raises(ValidationError):
            estimate_wait_minutes(position, 15)

    @pytest.mark.parametrize("duration", [0, -10, "15"])
    def test_invalid_duration_rejected(self, duration):
        with pytest.raises(ValidationError):
            estimate_wait_minutes(2, duration)


class TestEstimateQueueDrain:
    def test_empty_queue_drains_instantly(self):
        assert estimate_queue_drain(0, 15) == 0

    def test_drain_is_length_times_duration(self):
        assert estimate_queue_drain(4, 15) == 60

    def test_negative_length_rejected(self):
        with pytest.raises(ValidationError):
            estimate_queue_drain(-1, 15)

    def test_invalid_duration_rejected(self):
        with pytest.raises(ValidationError):
            estimate_queue_drain(3, 0)


class TestAlmostUp:
    def test_positions_inside_threshold(self):
        assert is_almost_up(1) is True
        assert is_almost_up(ALMOST_UP_THRESHOLD) is True

    def test_positions_outside_threshold(self):
        assert is_almost_up(ALMOST_UP_THRESHOLD + 1) is False
        assert is_almost_up(0) is False


class TestDescribeWait:
    def test_zero_reads_as_next(self):
        assert describe_wait(0) == "You are next"

    def test_negative_reads_as_next(self):
        assert describe_wait(-5) == "You are next"

    def test_minutes_under_an_hour(self):
        assert describe_wait(45) == "About 45 minutes"

    def test_whole_hours(self):
        assert describe_wait(60) == "About 1 hour"
        assert describe_wait(120) == "About 2 hours"

    def test_hours_and_minutes(self):
        assert describe_wait(95) == "About 1h 35m"


class TestWaitTimeEndpoint:
    def test_returns_estimate_for_empty_queue(self, client):
        data = client.get("/api/services/1/wait-time").get_json()
        assert data["queue_length"] == 0
        assert data["next_position"] == 1
        assert data["estimated_wait_minutes"] == 0
        assert data["wait_label"] == "You are next"

    def test_estimate_grows_as_people_join(self, client, auth, make_user):
        client.post("/api/services/1/queue/join", headers=auth)
        _, token = make_user()
        client.post(
            "/api/services/1/queue/join",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = client.get("/api/services/1/wait-time").get_json()
        assert data["queue_length"] == 2
        assert data["next_position"] == 3
        assert data["estimated_wait_minutes"] > 0

    def test_unknown_service_returns_404(self, client):
        assert client.get("/api/services/404/wait-time").status_code == 404
