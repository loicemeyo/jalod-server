from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort
from datetime import datetime, timedelta

try:
    from ..db import db
    from ..models.contribution import ContributionModel
    from ..models.member import memberModel
    from ..schemas.member import BirthdaySchema, MemberCreateSchema, MemberSchema, MemberUpdateSchema
    from ..schemas.contribution import ContributionSchema
except ImportError:  # pragma: no cover - allows running from src directory
    from db import db
    from models.contribution import ContributionModel
    from models.member import memberModel
    from schemas.member import BirthdaySchema, MemberCreateSchema, MemberSchema, MemberUpdateSchema
    from schemas.contribution import ContributionSchema

blp = Blueprint("members", __name__, description="Operations on members")


# Members resource: exposes CRUD for member records. Some endpoints are
# intentionally public (create/get/update) while others (list/delete) are
# protected by JWT to limit access to authenticated callers.


@blp.route("/members")
class Members(MethodView):
    @blp.response(200, schema=MemberSchema(many=True), description="Get all members")
    @jwt_required()
    def get(self):
        """Get all members"""
        return memberModel.query.all()

    @blp.arguments(MemberCreateSchema, location="json")
    @blp.response(201, schema=MemberSchema, description="Register a member")
    def post(self, payload):
        """Register a new member"""
        member = MemberSchema().load(payload, session=db.session)

        db.session.add(member)
        db.session.commit()

        return member, 201


@blp.route("/members/birthdays")
class MemberBirthdays(MethodView):
    @blp.response(200, schema=BirthdaySchema(many=True), description="Get all member birthdays")
    @jwt_required()
    def get(self):
        """Get all member birthdays"""
        birthdays = (
            memberModel.query.filter(memberModel.birthday.isnot(None))
            .order_by(memberModel.birthday.asc())
            .all()
        )

        return [
            {
                "id": member.id,
                "name": member.name,
                "birthday": member.birthday,
            }
            for member in birthdays
        ]


@blp.route("/members/me/contributions")
class MemberContributions(MethodView):
    @blp.response(200, schema=ContributionSchema(many=True), description="Get the authenticated member's contributions for the trailing 12 months")
    @jwt_required()
    def get(self):
        """Get the authenticated member's contributions for the trailing 12 months."""
        member_identity = get_jwt_identity()
        try:
            member_id = int(member_identity)
        except (TypeError, ValueError):
            abort(401, message="Invalid member identity")

        member = db.session.get(memberModel, member_id)
        if not member:
            abort(404, message="Member not found")

        cutoff_date = datetime.utcnow() - timedelta(days=365)

        return (
            ContributionModel.query.filter(ContributionModel.member_id == member.id)
            .filter(ContributionModel.date >= cutoff_date)
            .order_by(ContributionModel.date.asc())
            .all()
        )


@blp.route("/members/<int:member_id>")
class Member(MethodView):
    @blp.response(200, schema=MemberSchema, description="Get a member by ID")
    def get(self, member_id):
        """Get a member by ID"""
        # Use Session.get() to avoid the legacy Query.get() API.
        member = db.session.get(memberModel, member_id)
        if not member:
            abort(404, message="Member not found")

        return member

    @blp.arguments(MemberUpdateSchema, location="json")
    @blp.response(200, schema=MemberSchema, description="Edit a member")
    def put(self, payload, member_id):
        """Edit a member by ID"""
        # Use Session.get() rather than Query.get().
        member = db.session.get(memberModel, member_id)
        if not member:
            abort(404, message="Member not found")

        member = MemberSchema().load(payload, instance=member, partial=True, session=db.session)
        db.session.commit()
        return member

    @blp.response(204, description="Delete a member")
    @jwt_required()
    def delete(self, member_id):
        """Delete a member by ID"""
        # Use Session.get() rather than Query.get().
        member = db.session.get(memberModel, member_id)
        if not member:
            abort(404, message="Member not found")

        db.session.delete(member)
        db.session.commit()

        return f"Member deleted {member.name}", 204