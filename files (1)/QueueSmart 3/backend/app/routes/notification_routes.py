"""Notification endpoints."""

from flask import Blueprint, g, jsonify, request

from app.modules import notification_module
from app.routes import login_required

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notification_bp.get("")
@login_required
def list_notifications():
    unread_only = request.args.get("unread", "").lower() == "true"
    items = notification_module.list_for_user(g.current_user["id"], unread_only)
    return jsonify({
        "notifications": items,
        "unread_count": len([n for n in items if not n["read"]]),
    }), 200


@notification_bp.post("/read")
@login_required
def mark_read():
    return jsonify(notification_module.mark_all_read(g.current_user["id"])), 200
