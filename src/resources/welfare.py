from flask.views import MethodView
from flask_jwt_extended import jwt_required
from flask_smorest import Blueprint, abort
from sqlalchemy import extract

try:
    from ..db import db
    from ..logging_config import get_logger
    from ..models.welfare import WelfareModel
    from ..schemas.welfare import WelfareCreateSchema, WelfareSchema, WelfareUpdateSchema
    from ..models.member import memberModel
    from ..schemas.member import BirthdaySchema
    from ..schemas.welfare import WelfareMonthResponseSchema
except ImportError:  # pragma: no cover - allows running from src directory
    from db import db
    from logging_config import get_logger
    from models.welfare import WelfareModel
    from schemas.welfare import WelfareCreateSchema, WelfareSchema, WelfareUpdateSchema
    from models.member import memberModel
    from schemas.member import BirthdaySchema
    from schemas.welfare import WelfareMonthResponseSchema

logger = get_logger("jalod_api.welfare")

blp = Blueprint("welfare", __name__, description="Operations on welfare events")


@blp.route("/welfare")
class WelfareFunctions(MethodView):
    @blp.response(200, schema=WelfareSchema(many=True), description="Get all welfare events")
    def get(self):
        """Get all welfare events"""
        events = WelfareModel.query.order_by(WelfareModel.date.asc()).all()
        logger.info("Listed %d welfare events", len(events))
        return events

    @blp.arguments(WelfareCreateSchema, location="json")
    @blp.response(201, schema=WelfareSchema, description="Create a welfare event")
    @jwt_required()
    def post(self, payload):
        """Create a new welfare event"""
        welfare = WelfareSchema().load(payload, session=db.session)

        db.session.add(welfare)
        db.session.commit()
        logger.info(
            "Welfare event created: event_id=%s name=%s",
            welfare.id,
            welfare.event_name,
        )

        return welfare, 201


@blp.route("/welfare/<int:event_id>")
class WelfareEvent(MethodView):
    @blp.response(200, schema=WelfareSchema, description="Get a welfare event by ID")
    def get(self, event_id):
        """Get a welfare event by ID"""
        welfare = db.session.get(WelfareModel, event_id)
        if not welfare:
            logger.warning("Welfare event not found: event_id=%s", event_id)
            abort(404, message="Welfare event not found")

        return welfare

    @blp.arguments(WelfareUpdateSchema, location="json")
    @blp.response(200, schema=WelfareSchema, description="Edit a welfare event")
    @jwt_required()
    def put(self, payload, event_id):
        """Edit a welfare event by ID"""
        welfare = db.session.get(WelfareModel, event_id)
        if not welfare:
            logger.warning("Welfare event not found for update: event_id=%s", event_id)
            abort(404, message="Welfare event not found")

        welfare = WelfareSchema().load(payload, instance=welfare, partial=True, session=db.session)
        db.session.commit()
        logger.info("Welfare event updated: event_id=%s", event_id)
        return welfare

    @blp.response(204, description="Delete a welfare event")
    @jwt_required()
    def delete(self, event_id):
        """Delete a welfare event by ID"""
        welfare = db.session.get(WelfareModel, event_id)
        if not welfare:
            logger.warning("Welfare event not found for deletion: event_id=%s", event_id)
            abort(404, message="Welfare event not found")

        db.session.delete(welfare)
        db.session.commit()
        logger.info("Welfare event deleted: event_id=%s", event_id)

        return "", 204


@blp.route("/welfare/month/<int:year>/<int:month>")
class WelfareByMonth(MethodView):
    @blp.response(200, schema=WelfareMonthResponseSchema(), description="Get welfare events and birthdays for a given month")
    def get(self, year, month):
        """Get welfare events for a specific year and month (1-12) and member birthdays in that month."""
        if month < 1 or month > 12:
            abort(400, message="month must be between 1 and 12")

        events = (
            db.session.query(WelfareModel)
            .filter(extract("year", WelfareModel.date) == year)
            .filter(extract("month", WelfareModel.date) == month)
            .order_by(WelfareModel.date.asc())
            .all()
        )

        birthdays = (
            db.session.query(memberModel)
            .filter(memberModel.birthday.isnot(None))
            .filter(extract("month", memberModel.birthday) == month)
            .order_by(memberModel.birthday.asc())
            .all()
        )

        logger.info(
            "Welfare month query: year=%d month=%d events=%d birthdays=%d",
            year,
            month,
            len(events),
            len(birthdays),
        )
        return {"events": events, "birthdays": birthdays}
