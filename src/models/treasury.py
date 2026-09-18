try:
    from ..db import db
except ImportError:  # pragma: no cover - allows running from src directory
    from db import db


class TreasuryModel(db.Model):
    """Summary of the main account balance and total investments."""

    __tablename__ = "Treasury"

    id = db.Column(db.Integer, primary_key=True)
    main_account_balance = db.Column(db.Numeric(12, 2), nullable=True)
    account_balance_date = db.Column(db.DateTime, nullable=True)
    total_investments = db.Column(db.Numeric(12, 2), nullable=True)
    investments = db.relationship(
        "InvestmentModel",
        back_populates="treasury",
        cascade="all, delete-orphan",
    )


class InvestmentModel(db.Model):
    """A single investment recorded under the treasury summary."""

    __tablename__ = "Investments"

    id = db.Column(db.Integer, primary_key=True)
    treasury_id = db.Column(db.Integer, db.ForeignKey("Treasury.id"), nullable=False)
    investment_type = db.Column(
        db.Enum(
            "MMF",
            "boma_yangu",
            "government_bonds",
            "cryptocurrency",
            "land_asset",
            name="investment_type",
        ),
        nullable=False,
    )
    name = db.Column(db.String(255), nullable=False)
    initial_amount = db.Column(db.Numeric(12, 2), nullable=False)
    interest = db.Column(db.Numeric(12, 2), nullable=True)
    current_amount = db.Column(db.Numeric(12, 2), nullable=False)
    more_info = db.Column(db.Text, nullable=True)
    treasury = db.relationship("TreasuryModel", back_populates="investments")
