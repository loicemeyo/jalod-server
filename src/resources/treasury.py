from flask.views import MethodView
from flask_jwt_extended import get_jwt, jwt_required
from flask_smorest import Blueprint, abort

try:
    from ..logging_config import get_logger
except ImportError:  # pragma: no cover - allows running from src directory
    from logging_config import get_logger

logger = get_logger("jalod_api.treasury")

blp = Blueprint("treasury", __name__, description="Operations on treasury")


def _ensure_admin():
    """Abort with 403 unless the requester has the `admin` role in their JWT."""
    claims = get_jwt()
    if claims.get("role") != "admin":
        logger.warning(
            "Treasury access denied: non-admin user (role=%s)",
            claims.get("role"),
        )
        abort(403, message="Admin privileges required")


@blp.route("/treasury")
class Treasury(MethodView):
    @blp.response(200, description="Get all treasury data")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def get(self):
        """Get all treasury data"""
        _ensure_admin()
        logger.info("Treasury data fetched")
        return []
