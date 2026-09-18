"""split treasury summary and investments

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table_name: str) -> set[str]:
    if op.get_context().as_sql:
        return set()
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    if "Investments" not in existing_tables:
        op.create_table(
            "Investments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("treasury_id", sa.Integer(), nullable=False),
            sa.Column(
                "investment_type",
                sa.Enum(
                    "MMF",
                    "boma_yangu",
                    "government_bonds",
                    "cryptocurrency",
                    "land_asset",
                    name="investment_type",
                ),
                nullable=False,
            ),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("initial_amount", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("interest", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("current_amount", sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column("more_info", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["treasury_id"], ["Treasury.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    treasury_columns = _table_columns("Treasury")

    if "main_account_balance" not in treasury_columns and "current_balance" in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("main_account_balance", sa.Numeric(precision=12, scale=2), nullable=True))
            batch_op.execute("UPDATE Treasury SET main_account_balance = current_balance")

    if "account_balance_date" not in treasury_columns and "current_balance_date" in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("account_balance_date", sa.DateTime(), nullable=True))
            batch_op.execute("UPDATE Treasury SET account_balance_date = current_balance_date")

    if "total_investments" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("total_investments", sa.Numeric(precision=12, scale=2), nullable=True))

    for old_column in (
        "current_balance",
        "money_in_this_year",
        "money_out_this_year",
        "current_balance_date",
        "boma_yangu",
        "market_fund",
        "government_bonds",
        "cryptocurrency",
    ):
        if old_column in _table_columns("Treasury"):
            with op.batch_alter_table("Treasury") as batch_op:
                batch_op.drop_column(old_column)


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("Investments"):
        op.drop_table("Investments")

    treasury_columns = _table_columns("Treasury")

    if "current_balance" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("current_balance", sa.Numeric(precision=12, scale=2), nullable=True))

    if "current_balance_date" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("current_balance_date", sa.DateTime(), nullable=True))

    if "money_in_this_year" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("money_in_this_year", sa.Numeric(precision=12, scale=2), nullable=True))

    if "money_out_this_year" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("money_out_this_year", sa.Numeric(precision=12, scale=2), nullable=True))

    if "boma_yangu" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("boma_yangu", sa.Numeric(precision=12, scale=2), nullable=True))

    if "market_fund" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("market_fund", sa.Numeric(precision=12, scale=2), nullable=True))

    if "government_bonds" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("government_bonds", sa.Numeric(precision=12, scale=2), nullable=True))

    if "cryptocurrency" not in treasury_columns:
        with op.batch_alter_table("Treasury") as batch_op:
            batch_op.add_column(sa.Column("cryptocurrency", sa.Numeric(precision=12, scale=2), nullable=True))

    for new_column in ("main_account_balance", "account_balance_date", "total_investments"):
        if new_column in _table_columns("Treasury"):
            with op.batch_alter_table("Treasury") as batch_op:
                batch_op.drop_column(new_column)
