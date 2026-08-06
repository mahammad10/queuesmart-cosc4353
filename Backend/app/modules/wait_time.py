"""
Wait-Time Estimation Logic.

Rule-based, exactly as A3 allows. The rule is:

    estimated wait (minutes) = (position - 1) x expected duration

Position 1 is the person at the front, so their remaining wait is 0 - they are
next up. Everyone behind them waits for each person ahead to be served.

A priority multiplier lets high-priority services drain slightly faster than a
naive FIFO estimate, since staff typically fast-track them. It is a single
constant per level, not an algorithm, which keeps it inside A3's scope.
"""

from app.validators import ValidationError

# Higher weight = served earlier when two people are in the same queue.
PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}

# Multiplier applied to the raw estimate based on the entry's priority.
PRIORITY_MULTIPLIER = {"high": 0.8, "medium": 1.0, "low": 1.2}

# A user is warned they are "almost up" at this position or better.
ALMOST_UP_THRESHOLD = 2


def priority_weight(priority):
    """Sort weight for a priority label. Unknown labels fall back to medium."""
    return PRIORITY_WEIGHT.get(str(priority).lower(), PRIORITY_WEIGHT["medium"])


def estimate_wait_minutes(position, expected_duration, priority="medium"):
    """Estimated minutes until this position is served."""
    if not isinstance(position, int) or isinstance(position, bool) or position < 1:
        raise ValidationError("position", "Position must be a whole number of 1 or more.")

    if not isinstance(expected_duration, int) or expected_duration < 1:
        raise ValidationError(
            "expected_duration", "Expected duration must be at least 1 minute."
        )

    people_ahead = position - 1
    raw = people_ahead * expected_duration
    multiplier = PRIORITY_MULTIPLIER.get(str(priority).lower(), 1.0)

    return int(round(raw * multiplier))


def estimate_queue_drain(queue_length, expected_duration):
    """Minutes needed to clear the whole queue - shown on the admin screens."""
    if queue_length < 0:
        raise ValidationError("queue_length", "Queue length cannot be negative.")

    if expected_duration < 1:
        raise ValidationError(
            "expected_duration", "Expected duration must be at least 1 minute."
        )

    return queue_length * expected_duration


def is_almost_up(position):
    """True when the user is close enough to be served to warrant a warning."""
    return 1 <= position <= ALMOST_UP_THRESHOLD


def describe_wait(minutes):
    """Human-readable label used directly by the front end."""
    if minutes <= 0:
        return "You are next"

    if minutes < 60:
        return f"About {minutes} minutes"

    hours = minutes // 60
    remainder = minutes % 60

    if remainder == 0:
        return f"About {hours} hour" + ("s" if hours > 1 else "")

    return f"About {hours}h {remainder}m"
