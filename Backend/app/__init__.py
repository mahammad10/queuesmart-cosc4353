

import os

from flask import Flask, jsonify, send_from_directory

from app.validators import AuthError, ConflictError, NotFoundError, ValidationError

FRONTEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
)


def create_app(testing=False):
    app = Flask(__name__, static_folder=None)
    app.config["TESTING"] = testing
    app.config["JSON_SORT_KEYS"] = False

    from app.store import store

    if not store.users:
        store.reset()   # load the in-memory demo data

    register_blueprints(app)
    register_error_handlers(app)
    register_cors(app)
    register_frontend(app)

    return app


def register_blueprints(app):
    from app.routes.auth_routes import auth_bp
    from app.routes.history_routes import history_bp
    from app.routes.notification_routes import notification_bp
    from app.routes.queue_routes import queue_bp
    from app.routes.service_routes import service_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(service_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(history_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "QueueSmart API", "version": "1.0"})


def register_error_handlers(app):
 

    @app.errorhandler(ValidationError)
    def handle_validation(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(NotFoundError)
    def handle_not_found(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(ConflictError)
    def handle_conflict(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(AuthError)
    def handle_auth(error):
        return jsonify(error.to_dict()), error.status_code

    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({"error": "Not found", "message": "Unknown endpoint."}), 404

    @app.errorhandler(405)
    def handle_405(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def handle_500(error):  # pragma: no cover - safety net
        return jsonify({"error": "Server error"}), 500


def register_cors(app):
    """Allow the front end to be opened from a different origin during dev."""

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response

    @app.route("/api/<path:_any>", methods=["OPTIONS"])
    def preflight(_any):
        return ("", 204)


def register_frontend(app):
  

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename):
        return send_from_directory(FRONTEND_DIR, filename)
