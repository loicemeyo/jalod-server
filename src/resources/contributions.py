from decimal import Decimal

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

try:
    from ..db import db
    from ..logging_config import get_logger
    from ..models.contribution import ContributionModel
    from ..models.member import memberModel
    from ..models.treasury import TreasuryModel
    from ..schemas.contribution import ContributionCreateSchema, ContributionSchema, ContributionUpdateSchema
except ImportError:  # pragma: no cover - allows running from src directory
    from db import db
    from logging_config import get_logger
    from models.contribution import ContributionModel
    from models.member import memberModel
    from models.treasury import TreasuryModel
    from schemas.contribution import ContributionCreateSchema, ContributionSchema, ContributionUpdateSchema

logger = get_logger("jalod_api.contributions")

blp = Blueprint("contributions", __name__, description="Operations on contributions")


def _current_member_id() -> int:
    member_identity = get_jwt_identity()
    try:
        return int(member_identity)
    except (TypeError, ValueError):
        logger.warning("Invalid member identity in contribution request: %s", member_identity)
        abort(401, message="Invalid member identity")


def _load_current_member() -> memberModel:
    member_id = _current_member_id()
    member = db.session.get(memberModel, member_id)
    if not member:
        logger.warning("Member not found for contribution operation: member_id=%s", member_id)
        abort(404, message="Member not found")
    return member


def _load_owned_contribution(contribution_id: int) -> ContributionModel:
    member_id = _current_member_id()
    contribution = db.session.get(ContributionModel, contribution_id)
    if not contribution or contribution.member_id != member_id:
        logger.warning(
            "Contribution not found or access denied: contribution_id=%s member_id=%s",
            contribution_id,
            member_id,
        )
        abort(404, message="Contribution not found")
    return contribution


def _get_or_create_treasury() -> TreasuryModel:
    treasury = db.session.query(TreasuryModel).order_by(TreasuryModel.id.asc()).first()
    if treasury is None:
        treasury = TreasuryModel(
            main_account_balance=Decimal("0.00"),
            account_balance_date=None,
            total_investments=Decimal("0.00"),
        )
        db.session.add(treasury)
    return treasury


def _update_treasury_for_contribution(
    contribution_type: str,
    amount: Decimal,
    contribution_date,
    *,
    reverse: bool = False,
):
    treasury = _get_or_create_treasury()
    amount = abs(Decimal(str(amount)))
    signed_amount = -amount if reverse else amount

    if contribution_type in {"mpesa", "cash", "bank"}:
        current_balance = treasury.main_account_balance or Decimal("0.00")
        treasury.main_account_balance = current_balance + signed_amount
    elif contribution_type == "boma":
        current_balance = treasury.main_account_balance or Decimal("0.00")
        current_investments = treasury.total_investments or Decimal("0.00")
        treasury.main_account_balance = current_balance + signed_amount
        treasury.total_investments = current_investments + signed_amount

    treasury.account_balance_date = contribution_date
    db.session.add(treasury)


@blp.route("/contributions")
class Contributions(MethodView):
    @blp.arguments(ContributionCreateSchema, location="json")
    @blp.response(201, schema=ContributionSchema, description="Create a contribution")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def post(self, payload):
        """Create a contribution for the authenticated member."""
        member = _load_current_member()
        contribution = ContributionSchema().load(payload, session=db.session)
        contribution.member_id = member.id

        db.session.add(contribution)
        db.session.flush()
        _update_treasury_for_contribution(contribution.type, contribution.amount, contribution.date)
        db.session.commit()
        logger.info(
            "Contribution created: contribution_id=%s member_id=%s amount=%s type=%s",
            contribution.id,
            member.id,
            contribution.amount,
            contribution.type,
        )

        return contribution, 201


@blp.route("/contributions/<int:contribution_id>")
class Contribution(MethodView):
    @blp.response(200, schema=ContributionSchema, description="Get a contribution by ID")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def get(self, contribution_id):
        """Get one contribution owned by the authenticated member."""
        return _load_owned_contribution(contribution_id)

    @blp.arguments(ContributionUpdateSchema, location="json")
    @blp.response(200, schema=ContributionSchema, description="Edit a contribution")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def put(self, payload, contribution_id):
        """Edit a contribution owned by the authenticated member."""
        contribution = _load_owned_contribution(contribution_id)
        original_amount = Decimal(str(contribution.amount))
        original_type = contribution.type

        contribution = ContributionSchema().load(payload, instance=contribution, partial=True, session=db.session)
        contribution.member_id = _current_member_id()

        if original_type != contribution.type or original_amount != Decimal(str(contribution.amount)):
            _update_treasury_for_contribution(original_type, original_amount, contribution.date, reverse=True)
            _update_treasury_for_contribution(contribution.type, contribution.amount, contribution.date)

        db.session.commit()
        logger.info("Contribution updated: contribution_id=%s", contribution_id)
        return contribution

    @blp.response(204, description="Delete a contribution")
    @blp.doc(security=[{"bearerAuth": []}])
    @jwt_required()
    def delete(self, contribution_id):
        """Delete a contribution owned by the authenticated member."""
        contribution = _load_owned_contribution(contribution_id)
        _update_treasury_for_contribution(contribution.type, contribution.amount, contribution.date, reverse=True)
        db.session.delete(contribution)
        db.session.commit()
        logger.info("Contribution deleted: contribution_id=%s", contribution_id)

        return "", 204