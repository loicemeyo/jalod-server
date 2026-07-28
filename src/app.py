import logging
import os
import traceback

from dotenv import load_dotenv

from flask import Flask, g, request
from flask_smorest import Api
from flask_jwt_extended import JWTManager
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

try:
    from .db import configure_database, db, ensure_member_auth_columns
    from .logging_config import (
        configure_logging,
        get_logger,
        new_request_id,
        set_request_id,
    )
    from .resources.auth import blp as AuthBlueprint
    from .resources.contributions import blp as ContributionBlueprint
    from .resources.members import blp as MemberBlueprint
    from .resources.treasury import blp as TreasuryBlueprint
    from .resources.welfare import blp as WelfareBlueprint
    from .schemas import ma
    from .models.welfare import WelfareModel
    from .models.contribution import ContributionModel
except ImportError:  # pragma: no cover - allows running app.py directly
    from db import configure_database, db, ensure_member_auth_columns
    from logging_config import (
        configure_logging,
        get_logger,
        new_request_id,
        set_request_id,
    )
    from resources.auth import blp as AuthBlueprint
    from resources.contributions import blp as ContributionBlueprint
    from resources.members import blp as MemberBlueprint
    from resources.treasury import blp as TreasuryBlueprint
    from resources.welfare import blp as WelfareBlueprint
    from schemas import ma
    from models.welfare import WelfareModel
    from models.contribution import ContributionModel

# Ensure Flask-specific environment in `.flaskenv` is loaded during tests
# and when the app is created programmatically. Some environments (pytest)
# may not load .flaskenv automatically, so load it explicitly first.
load_dotenv(".flaskenv", override=True)
load_dotenv()

configure_logging("jalod_api")
logger = get_logger("jalod_api.app")

app = Flask(__name__)

app.config["PROPAGATE_EXCEPTIONS"] = True
app.config["API_TITLE"] = "Jalod Server API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")

configure_database(app)
ma.init_app(app)
api = Api(app)

api.spec.components.security_scheme(
    "bearerAuth",
    {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    },
)

api.register_blueprint(ContributionBlueprint)
api.register_blueprint(MemberBlueprint)
api.register_blueprint(AuthBlueprint)
api.register_blueprint(TreasuryBlueprint)
api.register_blueprint(WelfareBlueprint)

jwt = JWTManager(app)

with app.app_context():
    ensure_member_auth_columns(app)
    db.create_all()


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

@app.before_request
def _assign_request_id():
    rid = request.headers.get("X-Request-ID") or new_request_id()
    set_request_id(rid)
    g.request_id = rid


@app.after_request
def _log_response(response):
    rid = getattr(g, "request_id", "-")
    logger.info(
        "%s %s -> %s",
        request.method,
        request.path,
        response.status_code,
        extra={"status_code": response.status_code, "method": request.method, "path": request.path},
    )
    response.headers["X-Request-ID"] = rid
    return response


# ---------------------------------------------------------------------------
# Global error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(HTTPException)
def _handle_http_exception(exc):
    logger.warning(
        "HTTP error: %s %s -> %s (%s)",
        request.method,
        request.path,
        exc.code,
        exc.description,
        extra={"status_code": exc.code, "path": request.path},
    )
    return {"error": exc.description, "status_code": exc.code}, exc.code


@app.errorhandler(ValidationError)
def _handle_validation_error(exc):
    logger.warning(
        "Validation error: %s %s -> 400 (%s)",
        request.method,
        request.path,
        exc.messages,
        extra={"status_code": 400, "path": request.path, "validation_errors": exc.messages},
    )
    return {"error": "Validation failed", "details": exc.messages, "status_code": 400}, 400


@app.errorhandler(SQLAlchemyError)
def _handle_sqlalchemy_error(exc):
    logger.error(
        "Database error: %s %s -> 500 (%s)",
        request.method,
        request.path,
        str(exc),
        extra={"status_code": 500, "path": request.path},
        exc_info=True,
    )
    db.session.rollback()
    return {"error": "An internal database error occurred", "status_code": 500}, 500


@app.errorhandler(Exception)
def _handle_unexpected_exception(exc):
    logger.error(
        "Unhandled exception: %s %s -> 500 (%s)",
        request.method,
        request.path,
        str(exc),
        extra={"status_code": 500, "path": request.path},
        exc_info=True,
    )
    return {"error": "An unexpected internal error occurred", "status_code": 500}, 500


@app.route("/")
def hello_world():
    return "Welcome to the Jalod Server App!"

if __name__ == "__main__":
    app.run(debug=True)