from flask.views import MethodView
from flask_jwt_extended import create_access_token
from flask_smorest import Blueprint, abort

try:
    from ..models.member import memberModel
    from ..db import db
    from ..schemas.auth import AuthResponseSchema, LoginRequestSchema, SignupRequestSchema
    from ..logging_config import get_logger
except ImportError:  # pragma: no cover - allows running from src directory
    from models.member import memberModel
    from db import db
    from schemas.auth import AuthResponseSchema, LoginRequestSchema, SignupRequestSchema
    from logging_config import get_logger

logger = get_logger("jalod_api.auth")

blp = Blueprint("auth", __name__, description="Authentication operations")


def _parse_phone_number(value):
    if value is None:
        return None

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        stripped_value = value.strip()
        if not stripped_value:
            return None
        if stripped_value.isdigit():
            return int(stripped_value)

    abort(400, message="phone_number must be a valid number")


@blp.route("/auth/signup")
class SignUp(MethodView):
    @blp.arguments(SignupRequestSchema)
    @blp.response(201, schema=AuthResponseSchema, description="Create a new member account")
    def post(self, payload):
        name = payload["name"].strip()
        email_address = payload["email_address"].strip()
        phone_number = _parse_phone_number(payload["phone_number"])
        password = payload["password"]

        if memberModel.query.filter_by(name=name).first():
            logger.warning("Signup failed: name already exists (name=%s)", name)
            abort(409, message="Member with this name already exists")

        if memberModel.query.filter_by(email_address=email_address).first():
            logger.warning("Signup failed: email already exists (email=%s)", email_address)
            abort(409, message="Member with this email already exists")

        member = memberModel(
            name=name,
            email_address=email_address,
            phone_number=phone_number,
        )
        member.set_password(password)

        db.session.add(member)
        db.session.commit()
        logger.info("Signup successful: member_id=%s name=%s", member.id, member.name)

        token = create_access_token(
            identity=str(member.id),
            additional_claims={"name": member.name, "role": member.role},
        )
        return {
            "message": "Signup successful",
            "access_token": token,
            "member": {
                "id": member.id,
                "name": member.name,
                "email_address": member.email_address,
                "phone_number": member.phone_number,
                "role": member.role,
            },
        }, 201


@blp.route("/auth/login")
class Login(MethodView):
    @blp.arguments(LoginRequestSchema)
    @blp.response(200, schema=AuthResponseSchema, description="Login with name and password")
    def post(self, payload):
        name = payload["name"].strip()
        password = payload["password"]

        member = memberModel.query.filter_by(name=name).first()
        if not member or not member.check_password(password):
            logger.warning("Login failed: invalid credentials (name=%s)", name)
            abort(401, message="Invalid credentials")

        token = create_access_token(
            identity=str(member.id),
            additional_claims={"name": member.name, "role": member.role},
        )
        logger.info("Login successful: member_id=%s name=%s role=%s", member.id, member.name, member.role)
        return {
            "message": "Login successful",
            "access_token": token,
            "member": {
                "id": member.id,
                "name": member.name,
                "email_address": member.email_address,
                "phone_number": member.phone_number,
                "role": member.role,
            },
        }, 200