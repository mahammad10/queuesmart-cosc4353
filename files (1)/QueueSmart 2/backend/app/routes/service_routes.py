"""Service Management endpoints. Writes are administrator-only."""

from flask import Blueprint, jsonify, request

from app.modules import service_module
from app.routes import admin_required
from app.validators import validate_boolean

service_bp = Blueprint("services", __name__, url_prefix="/api/services")


@service_bp.get("")
def list_services():
    only_open = request.args.get("open", "").lower() == "true"
    return jsonify({"services": service_module.list_services(only_open)}), 200


@service_bp.get("/<int:service_id>")
def get_service(service_id):
    service = service_module.get_service(service_id)
    return jsonify({"service": service_module.serialize(service)}), 200


@service_bp.post("")
@admin_required
def create_service():
    service = service_module.create_service(request.get_json(silent=True))
    return jsonify({"service": service}), 201


@service_bp.put("/<int:service_id>")
@admin_required
def update_service(service_id):
    service = service_module.update_service(service_id, request.get_json(silent=True))
    return jsonify({"service": service}), 200


@service_bp.patch("/<int:service_id>/status")
@admin_required
def set_status(service_id):
    payload = request.get_json(silent=True) or {}
    is_open = validate_boolean(payload, "is_open", "Queue status")
    return jsonify({"service": service_module.set_open(service_id, is_open)}), 200


@service_bp.delete("/<int:service_id>")
@admin_required
def delete_service(service_id):
    return jsonify(service_module.delete_service(service_id)), 200
