from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

try:
    from ..db import db
    from ..models.contribution import ContributionModel
    from ..models.member import memberModel
    from ..schemas.contribution import ContributionCreateSchema, ContributionSchema, ContributionUpdateSchema
except ImportError:  # pragma: no cover - allows running from src directory
    from db import db
    from models.contribution import ContributionModel
    from models.member import memberModel
    from schemas.contribution import ContributionCreateSchema, ContributionSchema, ContributionUpdateSchema


blp = Blueprint("contributions", __name__, description="Operations on contributions")


def _current_member_id() -> int:
    member_identity = get_jwt_identity()
    try:
        return int(member_identity)
    except (TypeError, ValueError):
        abort(401, message="Invalid member identity")


def _load_current_member() -> memberModel:
    member_id = _current_member_id()
    member = db.session.get(memberModel, member_id)
    if not member:
        abort(404, message="Member not found")
    return member


def _load_owned_contribution(contribution_id: int) -> ContributionModel:
    member_id = _current_member_id()
    contribution = db.session.get(ContributionModel, contribution_id)
    if not contribution or contribution.member_id != member_id:
        abort(404, message="Contribution not found")
    return contribution


@blp.route("/contributions")
class Contributions(MethodView):
    @blp.arguments(ContributionCreateSchema, location="json")
    @blp.response(201, schema=ContributionSchema, description="Create a contribution")
    @jwt_required()
    def post(self, payload):
        """Create a contribution for the authenticated member."""
        member = _load_current_member()
        contribution = ContributionSchema().load(payload, session=db.session)
        contribution.member_id = member.id

        db.session.add(contribution)
        db.session.commit()

        return contribution, 201


@blp.route("/contributions/<int:contribution_id>")
class Contribution(MethodView):
    @blp.response(200, schema=ContributionSchema, description="Get a contribution by ID")
    @jwt_required()
    def get(self, contribution_id):
        """Get one contribution owned by the authenticated member."""
        return _load_owned_contribution(contribution_id)

    @blp.arguments(ContributionUpdateSchema, location="json")
    @blp.response(200, schema=ContributionSchema, description="Edit a contribution")
    @jwt_required()
    def put(self, payload, contribution_id):
        """Edit a contribution owned by the authenticated member."""
        contribution = _load_owned_contribution(contribution_id)
        contribution = ContributionSchema().load(payload, instance=contribution, partial=True, session=db.session)
        contribution.member_id = _current_member_id()

        db.session.commit()
        return contribution

    @blp.response(204, description="Delete a contribution")
    @jwt_required()
    def delete(self, contribution_id):
        """Delete a contribution owned by the authenticated member."""
        contribution = _load_owned_contribution(contribution_id)
        db.session.delete(contribution)
        db.session.commit()

        return "", 204