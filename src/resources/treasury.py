from datetime import UTC, datetime
from decimal import Decimal

from flask.views import MethodView
from flask_jwt_extended import get_jwt, jwt_required
from flask_smorest import Blueprint, abort
from marshmallow import Schema, fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

try:
    from ..db import db
    from ..logging_config import get_logger
    from ..models.treasury import InvestmentModel, TreasuryModel
except ImportError:  # pragma: no cover - allows running from src directory
    from db import db
    from logging_config import get_logger
    from models.treasury import InvestmentModel, TreasuryModel

logger = get_logger("jalod_api.treasury")

blp = Blueprint("treasury", __name__, description="Operations on treasury")


class InvestmentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = InvestmentModel
        load_instance = True
        sqla_session = db.session
        include_fk = True
        include_relationships = False

    investment_type = fields.String(required=True)
    name = fields.String(required=True)
    initial_amount = fields.Decimal(required=True, as_string=True)
    interest = fields.Decimal(allow_none=True, as_string=True)
    current_amount = fields.Decimal(required=True, as_string=True)
    more_info = fields.String(allow_none=True)


class TreasurySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TreasuryModel
        load_instance = True
        sqla_session = db.session
        include_relationships = True

    main_account_balance = fields.Decimal(allow_none=True, as_string=True)
    account_balance_date = fields.DateTime(allow_none=True)
    total_investments = fields.Decimal(allow_none=True, as_string=True)


class TreasuryWithdrawalSchema(Schema):
    amount = fields.Decimal(required=True, as_string=True)
    details = fields.String(load_default=None, allow_none=True)


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
    @blp.response(200, schema=TreasurySchema(many=True), description="Get all treasury data")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def get(self):
        """Get all treasury data for authenticated users."""
        treasury_data = TreasuryModel.query.order_by(TreasuryModel.id.asc()).all()
        logger.info("Treasury data fetched: count=%s", len(treasury_data))
        return treasury_data


@blp.route("/treasury/withdrawals")
class TreasuryWithdrawal(MethodView):
    @blp.arguments(TreasuryWithdrawalSchema, location="json")
    @blp.response(200, schema=TreasurySchema, description="Record an admin withdrawal from the main account")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def post(self, payload):
        """Reduce the treasury main account balance for a withdrawal."""
        _ensure_admin()
        treasury = db.session.query(TreasuryModel).order_by(TreasuryModel.id.asc()).first()
        if treasury is None:
            treasury = TreasuryModel(
                main_account_balance=0,
                account_balance_date=None,
                total_investments=0,
            )
            db.session.add(treasury)
            db.session.flush()

        withdrawal_amount = Decimal(str(payload["amount"]))
        if withdrawal_amount <= 0:
            abort(400, message="Withdrawal amount must be greater than zero")

        treasury.main_account_balance = (treasury.main_account_balance or Decimal("0.00")) - withdrawal_amount
        treasury.account_balance_date = datetime.now(UTC)
        db.session.commit()

        logger.info(
            "Treasury withdrawal recorded: amount=%s details=%s remaining_balance=%s",
            withdrawal_amount,
            payload.get("details"),
            treasury.main_account_balance,
        )
        return treasury


@blp.route("/treasury/investments")
class TreasuryInvestments(MethodView):
    @blp.response(200, schema=InvestmentSchema(many=True), description="Get all investments")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def get(self):
        """Get all investments."""
        investments = InvestmentModel.query.order_by(InvestmentModel.id.asc()).all()
        logger.info("Fetched %d investments", len(investments))
        return investments


@blp.route("/treasury/investments/<int:investment_id>")
class TreasuryInvestment(MethodView):
    @blp.response(200, schema=InvestmentSchema, description="Get an investment by ID")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def get(self, investment_id):
        """Get a single investment by ID."""
        investment = db.session.get(InvestmentModel, investment_id)
        if not investment:
            logger.warning("Investment not found: investment_id=%s", investment_id)
            abort(404, message="Investment not found")
        logger.info("Investment fetched: investment_id=%s", investment_id)
        return investment
