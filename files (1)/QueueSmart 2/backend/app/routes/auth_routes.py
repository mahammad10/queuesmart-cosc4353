"""Authentication endpoints."""

from flask import Blueprint, g, jsonify, request

from app.modules import auth_module
from app.routes import _token_from_request, login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    result = auth_module.register_user(request.get_json(silent=True))
    return jsonify(result), 201


@auth_bp.post("/login")
def login():
    result = auth_module.login_user(request.get_json(silent=True))
    return jsonify(result), 200


@auth_bp.post("/logout")
@login_required
def logout():
    return jsonify(auth_module.logout(_token_from_request())), 200


@auth_bp.get("/me")
@login_required
def me():
    return jsonify({"user": auth_module.public_user(g.current_user)}), 200
