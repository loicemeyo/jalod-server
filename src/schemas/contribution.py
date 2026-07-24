from marshmallow import fields
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

    id = fields.Int(dump_only=True)
    member_id = fields.Int(dump_only=True)
    amount = fields.Decimal(required=True)
    date = fields.DateTime(required=True)
    type = fields.String(required=True)