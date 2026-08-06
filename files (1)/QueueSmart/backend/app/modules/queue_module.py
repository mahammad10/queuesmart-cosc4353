"""
Queue Management Module.

Ordering rule
-------------
Entries are sorted by priority first, then by arrival order:

    sort key = (-priority_weight, arrival_sequence)

high(3) beats medium(2) beats low(1). Inside one priority level the person who
arrived first is served first, because `arrival_sequence` is a global counter
that only ever increases. An entry inherits its service's priority level
unless an administrator overrides it.
"""

from datetime import datetime, timezone

from app.modules import history_module, notification_module, service_module
from app.modules.wait_time import (
    describe_wait,
    estimate_queue_drain,
    estimate_wait_minutes,
    is_almost_up,
    priority_weight,
)
from app.store import store
from app.validators import (
    ConflictError,
    NotFoundError,
    VALID_PRIORITIES,
    require_payload,
    validate_choice,
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sort_key(entry):
    return (-priority_weight(entry["priority"]), entry["arrival_sequence"])


def ordered_entries(service_id):
    """The queue for one service, in the order people will actually be served."""
    return sorted(store.get_queue(service_id), key=_sort_key)


def find_entry(service_id, user_id):
    """The queue entry belonging to a user, or None."""
    for entry in store.get_queue(service_id):
        if entry["user_id"] == user_id:
            return entry
    return None


def get_position(service_id, user_id):
    """1-based position, or None if the user is not in this queue."""
    for index, entry in enumerate(ordered_entries(service_id)):
        if entry["user_id"] == user_id:
            return index + 1
    return None


def serialize_entry(entry, position, service):
    minutes = estimate_wait_minutes(position, service["expected_duration"], entry["priority"])

    return {
        "entry_id": entry["id"],
        "user_id": entry["user_id"],
        "user_name": entry["user_name"],
        "service_id": service["id"],
        "service_name": service["name"],
        "priority": entry["priority"],
        "position": position,
        "joined_at": entry["joined_at"],
        "estimated_wait_minutes": minutes,
        "wait_label": describe_wait(minutes),
    }


def view_queue(service_id):
    """Full queue view used by the admin Queue Management page."""
    service = service_module.get_service(service_id)
    entries = ordered_entries(service_id)

    return {
        "service": service_module.serialize(service),
        "queue_length": len(entries),
        "estimated_drain_minutes": estimate_queue_drain(
            len(entries), service["expected_duration"]
        ),
        "entries": [
            serialize_entry(entry, index + 1, service)
            for index, entry in enumerate(entries)
        ],
    }


def join_queue(user, service_id, data=None):
    """Add a user to a service queue and open a history record."""
    service = service_module.get_service(service_id)

    if not service["is_open"]:
        raise ConflictError(f"{service['name']} is not accepting new users right now.")

    if get_position(service_id, user["id"]) is not None:
        raise ConflictError(f"You are already in the {service['name']} queue.")

    priority = validate_choice(
        require_payload(data or {}),
        "priority",
        "Priority level",
        VALID_PRIORITIES,
        default=service["priority"],
    )

    entry = {
        "id": store.next_entry_id(),
        "service_id": service_id,
        "user_id": user["id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "priority": priority,
        "arrival_sequence": store.next_sequence(),
        "joined_at": _now(),
        "almost_up_notified": False,
    }

    store.get_queue(service_id).append(entry)

    position = get_position(service_id, user["id"])
    minutes = estimate_wait_minutes(position, service["expected_duration"], priority)

    history_module.open_record(user, service, position)
    notification_module.notify_joined(user, service, position, minutes)
    refresh_almost_up(service_id)

    return serialize_entry(entry, position, service)


def leave_queue(user, service_id):
    """The user withdraws voluntarily."""
    service = service_module.get_service(service_id)
    queue = store.get_queue(service_id)

    match = next((e for e in queue if e["user_id"] == user["id"]), None)

    if not match:
        raise NotFoundError(f"You are not in the {service['name']} queue.")

    queue.remove(match)

    history_module.close_record(user["id"], service_id, history_module.STATUS_LEFT)
    notification_module.notify_left(user["id"], service)
    refresh_almost_up(service_id)

    return {"message": f"You left the {service['name']} queue.", "service_id": service_id}


def remove_entry(service_id, entry_id):
    """Administrator removes somebody from the queue."""
    service = service_module.get_service(service_id)
    queue = store.get_queue(service_id)

    match = next((e for e in queue if e["id"] == entry_id), None)

    if not match:
        raise NotFoundError(f"Queue entry {entry_id} does not exist.")

    queue.remove(match)

    history_module.close_record(match["user_id"], service_id, history_module.STATUS_REMOVED)
    notification_module.push(
        match["user_id"],
        f"You were removed from the {service['name']} queue by an administrator.",
        "queue_left",
        service_id,
    )
    refresh_almost_up(service_id)

    return {"message": f"{match['user_name']} was removed from the queue."}


def serve_next(service_id):
    """Serve the person at the front of the queue."""
    service = service_module.get_service(service_id)
    entries = ordered_entries(service_id)

    if not entries:
        raise ConflictError(f"The {service['name']} queue is empty.")

    served = entries[0]
    store.get_queue(service_id).remove(served)

    record = history_module.close_record(
        served["user_id"], service_id, history_module.STATUS_SERVED
    )
    notification_module.notify_served(served["user_id"], service)
    refresh_almost_up(service_id)

    return {
        "served": {
            "entry_id": served["id"],
            "user_id": served["user_id"],
            "user_name": served["user_name"],
            "priority": served["priority"],
            "actual_wait_minutes": record["actual_wait_minutes"] if record else None,
        },
        "remaining": len(store.get_queue(service_id)),
        "service_id": service_id,
    }


def move_entry(service_id, entry_id, direction):
    """
    Manual admin override: swap an entry with its neighbour.

    The two entries trade both priority and arrival_sequence, so the swap holds
    even when they sit in different priority bands.
    """
    service_module.get_service(service_id)
    entries = ordered_entries(service_id)

    index = next((i for i, e in enumerate(entries) if e["id"] == entry_id), None)

    if index is None:
        raise NotFoundError(f"Queue entry {entry_id} does not exist.")

    target = index + (1 if direction == "down" else -1)

    if target < 0 or target >= len(entries):
        raise ConflictError("That entry cannot move any further.")

    a, b = entries[index], entries[target]

    a["priority"], b["priority"] = b["priority"], a["priority"]
    a["arrival_sequence"], b["arrival_sequence"] = b["arrival_sequence"], a["arrival_sequence"]

    refresh_almost_up(service_id)

    return view_queue(service_id)


def user_status(user):
    """Every queue the signed-in user is currently sitting in."""
    active = []

    for service_id in list(store.queues.keys()):
        position = get_position(service_id, user["id"])

        if position is None:
            continue

        service = store.services.get(service_id)

        if not service:
            continue

        entry = next(
            e for e in store.get_queue(service_id) if e["user_id"] == user["id"]
        )
        active.append(serialize_entry(entry, position, service))

    return {"in_queue": len(active) > 0, "queues": active}


def refresh_almost_up(service_id):
    """
    Fire an 'almost your turn' notification for anyone who has moved into the
    warning band, and reset the flag for anyone who fell back out of it.
    """
    service = store.services.get(service_id)

    if not service:
        return []

    fired = []

    for index, entry in enumerate(ordered_entries(service_id)):
        position = index + 1

        if is_almost_up(position) and not entry["almost_up_notified"]:
            entry["almost_up_notified"] = True
            fired.append(
                notification_module.notify_almost_up(entry["user_id"], service, position)
            )
        elif not is_almost_up(position):
            entry["almost_up_notified"] = False

    return fired
