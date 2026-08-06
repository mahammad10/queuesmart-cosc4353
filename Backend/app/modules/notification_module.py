"""
Notification Module.

No email or SMS is sent. Notifications are appended to an in-memory log and
returned to the front end, which renders them on the dashboard.

Triggers:
  * queue_joined  - the user takes a place in a queue
  * almost_up     - the user reaches position 1 or 2
  * served        - the user has been called
  * queue_left    - the user withdrew
  * service       - admin changed a service (open/closed/created/updated)
"""

from datetime import datetime, timezone

from app.store import store

VALID_TYPES = ("queue_joined", "almost_up", "served", "queue_left", "service", "system")


def _now():
    return datetime.now(timezone.utc).isoformat()


def push(user_id, message, notification_type="system", service_id=None):
    """Record a notification. user_id=None means it is a broadcast."""
    notification = {
        "id": store.next_notification_id(),
        "user_id": user_id,
        "service_id": service_id,
        "type": notification_type if notification_type in VALID_TYPES else "system",
        "message": message,
        "read": False,
        "created_at": _now(),
    }

    store.notifications.append(notification)

    return notification


def notify_joined(user, service, position, wait_minutes):
    return push(
        user["id"],
        f"You joined {service['name']}. You are number {position} in line "
        f"with an estimated wait of {wait_minutes} minutes.",
        "queue_joined",
        service["id"],
    )


def notify_almost_up(user_id, service, position):
    return push(
        user_id,
        f"Almost your turn for {service['name']} - you are number {position} in line. "
        "Please head to the counter.",
        "almost_up",
        service["id"],
    )


def notify_served(user_id, service):
    return push(
        user_id,
        f"You are being served now for {service['name']}.",
        "served",
        service["id"],
    )


def notify_left(user_id, service):
    return push(
        user_id,
        f"You left the {service['name']} queue.",
        "queue_left",
        service["id"],
    )


def list_for_user(user_id, unread_only=False, limit=20):
    """Newest first. Broadcasts (user_id=None) are visible to everyone."""
    items = [
        n for n in store.notifications
        if n["user_id"] == user_id or n["user_id"] is None
    ]

    if unread_only:
        items = [n for n in items if not n["read"]]

    items = sorted(items, key=lambda n: n["id"], reverse=True)

    return items[:limit]


def mark_all_read(user_id):
    count = 0

    for notification in store.notifications:
        if notification["user_id"] == user_id and not notification["read"]:
            notification["read"] = True
            count += 1

    return {"marked_read": count}
