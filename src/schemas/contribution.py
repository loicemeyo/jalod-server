from marshmallow import fields
from marshmallow import Schema, validate
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

try:
    from ..db import db
    from ..models.contribution import ContributionModel
except ImportError:  # pragma: no cover - allows running from src directory
    from db import db
    from models.contribution import ContributionModel


class ContributionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ContributionModel
        load_instance = True
        sqla_session = db.session
        include_relationships = False
        exclude = ("type",)

    id = fields.Int(dump_only=True)
    member_id = fields.Int(dump_only=True)
    amount = fields.Decimal(required=True, as_string=True)
    date = fields.DateTime(required=True)
    contribution_type = fields.String(required=True, attribute="type", validate=validate.OneOf(["boma", "mpesa", "cash", "bank"]))


class ContributionCreateSchema(Schema):
    amount = fields.Decimal(required=True, as_string=True)
    date = fields.DateTime(required=True)
    contribution_type = fields.String(required=True, validate=validate.OneOf(["boma", "mpesa", "cash", "bank"]))


class ContributionUpdateSchema(Schema):
    amount = fields.Decimal(as_string=True)
    date = fields.DateTime()
    contribution_type = fields.String(validate=validate.OneOf(["boma", "mpesa", "cash", "bank"]))