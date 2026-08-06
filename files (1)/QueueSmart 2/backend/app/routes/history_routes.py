"""History endpoints."""

from flask import Blueprint, g, jsonify, request

from app.modules import history_module
from app.routes import admin_required, login_required

history_bp = Blueprint("history", __name__, url_prefix="/api/history")


@history_bp.get("")
@login_required
def my_history():
    status = request.args.get("status")
    return jsonify({
        "history": history_module.list_for_user(g.current_user["id"], status),
        "summary": history_module.summary_for_user(g.current_user["id"]),
    }), 200


@history_bp.get("/service/<int:service_id>")
@admin_required
def service_history(service_id):
    return jsonify({"history": history_module.list_for_service(service_id)}), 200
