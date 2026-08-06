"""
Service Management Module.

A service is anything a customer can queue for. Each one carries a name,
description, expected duration (minutes) and a priority level that also acts
as the default priority for people who join its queue.
"""

from datetime import datetime, timezone

from app.store import store
from app.validators import (
    ConflictError,
    MAX_DESCRIPTION_LENGTH,
    MAX_DURATION,
    MAX_SERVICE_NAME_LENGTH,
    MIN_DURATION,
    NotFoundError,
    VALID_PRIORITIES,
    require_payload,
    validate_boolean,
    validate_choice,
    validate_integer,
    validate_string,
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def validate_service(data, partial=False):
    """Validate a service payload. partial=True is used for updates."""
    data = require_payload(data)
    cleaned = {}

    if not partial or "name" in data:
        cleaned["name"] = validate_string(
            data, "name", "Service name", MAX_SERVICE_NAME_LENGTH, min_length=2
        )

    if not partial or "description" in data:
        cleaned["description"] = validate_string(
            data, "description", "Description", MAX_DESCRIPTION_LENGTH
        )

    if not partial or "expected_duration" in data:
        cleaned["expected_duration"] = validate_integer(
            data,
            "expected_duration",
            "Expected duration",
            minimum=MIN_DURATION,
            maximum=MAX_DURATION,
        )

    if not partial or "priority" in data:
        cleaned["priority"] = validate_choice(
            data, "priority", "Priority level", VALID_PRIORITIES, default="medium"
        )

    if "is_open" in data:
        cleaned["is_open"] = validate_boolean(data, "is_open", "Queue status", default=True)

    return cleaned


def serialize(service):
    """Service dict plus the live queue length, which the UI displays."""
    data = dict(service)
    data["queue_length"] = len(store.get_queue(service["id"]))
    return data


def list_services(only_open=False):
    services = [serialize(s) for s in store.services.values()]

    if only_open:
        services = [s for s in services if s["is_open"]]

    return sorted(services, key=lambda s: s["id"])


def get_service(service_id):
    service = store.services.get(service_id)

    if not service:
        raise NotFoundError(f"Service {service_id} does not exist.")

    return service


def create_service(data):
    cleaned = validate_service(data)

    name_taken = any(
        s["name"].lower() == cleaned["name"].lower() for s in store.services.values()
    )
    if name_taken:
        raise ConflictError("A service with that name already exists.")

    service = {
        "id": store.next_service_id(),
        "name": cleaned["name"],
        "description": cleaned["description"],
        "expected_duration": cleaned["expected_duration"],
        "priority": cleaned["priority"],
        "is_open": cleaned.get("is_open", True),
        "created_at": _now(),
    }

    store.services[service["id"]] = service
    store.queues[service["id"]] = []

    return serialize(service)


def update_service(service_id, data):
    service = get_service(service_id)
    cleaned = validate_service(data, partial=True)

    if "name" in cleaned:
        clash = any(
            s["id"] != service_id and s["name"].lower() == cleaned["name"].lower()
            for s in store.services.values()
        )
        if clash:
            raise ConflictError("A service with that name already exists.")

    service.update(cleaned)

    return serialize(service)


def set_open(service_id, is_open):
    service = get_service(service_id)
    service["is_open"] = bool(is_open)
    return serialize(service)


def delete_service(service_id):
    service = get_service(service_id)

    store.services.pop(service_id, None)
    store.queues.pop(service_id, None)

    return {"message": f"{service['name']} was deleted.", "id": service_id}
