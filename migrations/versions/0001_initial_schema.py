"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-03

Baseline migration that creates the four application tables: Members,
Contributions, Treasury and Welfare.

It is written to be tolerant of databases that already contain these tables
(for example deployments that were created earlier by ``db.create_all()`` at
startup), so it can be applied to both fresh and existing databases.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    """Return the set of table names currently present in the database.

    In offline mode there is no live connection to inspect, so it is assumed
    that the target schema does not exist yet.
    """
    if op.get_context().as_sql:
        return set()
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _existing_tables()

    if "Members" not in existing:
        op.create_table(
            "Members",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=40), nullable=False),
            sa.Column("email_address", sa.String(length=40), nullable=False),
            sa.Column("phone_number", sa.Integer(), nullable=False),
            sa.Column("birthday", sa.DateTime(), nullable=True),
            sa.Column("age_group", sa.String(length=20), nullable=True),
            sa.Column("total_contributions", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("contributions_predated", sa.DateTime(), nullable=True),
            sa.Column("password_hash", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("contributions_tier", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("contributions_debt", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("loans_debt", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column("contributions_dated_at", sa.DateTime(), nullable=True),
            sa.Column("role", sa.String(length=10), nullable=False, server_default="user"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
            sa.UniqueConstraint("email_address"),
        )

    if "Contributions" not in existing:
        op.create_table(
            "Contributions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("date", sa.DateTime(), nullable=False),
            sa.Column(
                "type",
                sa.Enum("boma", "mpesa", "cash", "bank", name="contribution_type"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["member_id"], ["Members.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if "Treasury" not in existing:
        op.create_table(
            "Treasury",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("current_balance", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("money_in_this_year", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("money_out_this_year", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("current_balance_date", sa.DateTime(), nullable=True),
            sa.Column("boma_yangu", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("market_fund", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("government_bonds", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("cryptocurrency", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if "Welfare" not in existing:
        op.create_table(
            "Welfare",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("event_id", sa.Integer(), nullable=False),
            sa.Column("event_name", sa.String(length=100), nullable=False),
            sa.Column("date", sa.DateTime(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("amount_spent", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column(
                "status",
                sa.Enum("Done", "Not Completed", name="welfare_status"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    existing = _existing_tables()

    # Contributions references Members, so drop it before Members.
    for table_name in ("Welfare", "Treasury", "Contributions", "Members"):
        if table_name in existing:
            op.drop_table(table_name)
