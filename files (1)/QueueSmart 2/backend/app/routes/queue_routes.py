"""Queue Management and wait-time endpoints."""

from flask import Blueprint, g, jsonify, request

from app.modules import queue_module, service_module
from app.modules.wait_time import describe_wait, estimate_queue_drain
from app.routes import admin_required, login_required
from app.validators import validate_choice

queue_bp = Blueprint("queues", __name__, url_prefix="/api")


# ----------------------------------------------------------------------
# User actions
# ----------------------------------------------------------------------

@queue_bp.post("/services/<int:service_id>/queue/join")
@login_required
def join(service_id):
    entry = queue_module.join_queue(g.current_user, service_id, request.get_json(silent=True))
    return jsonify({"entry": entry}), 201


@queue_bp.delete("/services/<int:service_id>/queue/leave")
@login_required
def leave(service_id):
    return jsonify(queue_module.leave_queue(g.current_user, service_id)), 200


@queue_bp.get("/queue/status")
@login_required
def my_status():
    return jsonify(queue_module.user_status(g.current_user)), 200


# ----------------------------------------------------------------------
# Wait-time estimation
# ----------------------------------------------------------------------

@queue_bp.get("/services/<int:service_id>/wait-time")
def wait_time(service_id):
    """Estimated wait for somebody joining this queue right now."""
    service = service_module.get_service(service_id)
    queue_length = len(queue_module.ordered_entries(service_id))

    from app.modules.wait_time import estimate_wait_minutes

    minutes = estimate_wait_minutes(
        queue_length + 1, service["expected_duration"], service["priority"]
    )

    return jsonify({
        "service_id": service_id,
        "service_name": service["name"],
        "queue_length": queue_length,
        "next_position": queue_length + 1,
        "estimated_wait_minutes": minutes,
        "wait_label": describe_wait(minutes),
        "estimated_drain_minutes": estimate_queue_drain(
            queue_length, service["expected_duration"]
        ),
    }), 200


# ----------------------------------------------------------------------
# Administrator actions
# ----------------------------------------------------------------------

@queue_bp.get("/services/<int:service_id>/queue")
@admin_required
def view_queue(service_id):
    return jsonify(queue_module.view_queue(service_id)), 200


@queue_bp.post("/services/<int:service_id>/queue/serve-next")
@admin_required
def serve_next(service_id):
    return jsonify(queue_module.serve_next(service_id)), 200


@queue_bp.delete("/services/<int:service_id>/queue/<int:entry_id>")
@admin_required
def remove_entry(service_id, entry_id):
    return jsonify(queue_module.remove_entry(service_id, entry_id)), 200


@queue_bp.patch("/services/<int:service_id>/queue/<int:entry_id>/move")
@admin_required
def move_entry(service_id, entry_id):
    payload = request.get_json(silent=True) or {}
    direction = validate_choice(payload, "direction", "Direction", ("up", "down"))
    return jsonify(queue_module.move_entry(service_id, entry_id, direction)), 200
