"""
History Module.

Every queue participation produces one history record. The record is opened
when the user joins and closed when they are served or leave, so the same row
carries the outcome and the actual time spent waiting.
"""

from datetime import datetime, timezone

from app.store import store

STATUS_WAITING = "waiting"
STATUS_SERVED = "served"
STATUS_LEFT = "left"
STATUS_REMOVED = "removed"


def _now():
    return datetime.now(timezone.utc)


def open_record(user, service, position):
    record = {
        "id": store.next_history_id(),
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "service_id": service["id"],
        "service_name": service["name"],
        "joined_at": _now().isoformat(),
        "ended_at": None,
        "position_at_join": position,
        "status": STATUS_WAITING,
        "actual_wait_minutes": None,
    }

    store.history.append(record)

    return record


def find_open_record(user_id, service_id):
    for record in reversed(store.history):
        if (
            record["user_id"] == user_id
            and record["service_id"] == service_id
            and record["status"] == STATUS_WAITING
        ):
            return record
    return None


def close_record(user_id, service_id, status):
    """Mark an open record finished and compute the real wait."""
    record = find_open_record(user_id, service_id)

    if not record:
        return None

    ended = _now()
    joined = datetime.fromisoformat(record["joined_at"])

    if joined.tzinfo is None:
        joined = joined.replace(tzinfo=timezone.utc)

    record["ended_at"] = ended.isoformat()
    record["status"] = status
    record["actual_wait_minutes"] = max(
        0, int(round((ended - joined).total_seconds() / 60))
    )

    return record


def list_for_user(user_id, status=None):
    """Newest first."""
    records = [r for r in store.history if r["user_id"] == user_id]

    if status:
        records = [r for r in records if r["status"] == status]

    return sorted(records, key=lambda r: r["id"], reverse=True)


def list_for_service(service_id):
    records = [r for r in store.history if r["service_id"] == service_id]
    return sorted(records, key=lambda r: r["id"], reverse=True)


def summary_for_user(user_id):
    records = list_for_user(user_id)
    served = [r for r in records if r["status"] == STATUS_SERVED]
    waits = [r["actual_wait_minutes"] for r in served if r["actual_wait_minutes"] is not None]

    return {
        "total_visits": len(records),
        "served": len(served),
        "left": len([r for r in records if r["status"] == STATUS_LEFT]),
        "average_wait_minutes": int(round(sum(waits) / len(waits))) if waits else 0,
    }
