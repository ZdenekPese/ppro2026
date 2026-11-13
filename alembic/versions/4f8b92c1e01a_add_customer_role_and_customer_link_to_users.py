"""add customer role and customer link to users

Revision ID: 4f8b92c1e01a
Revises: ddeddcf0b732
Create Date: 2026-11-13 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f8b92c1e01a"
down_revision: Union[str, None] = "ddeddcf0b732"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_users_valid_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_valid_role",
        "users",
        "role IN ('manager', 'warehouse', 'customer')",
    )
    op.add_column("users", sa.Column("customer_id", sa.UUID(), nullable=True))
    op.create_index(op.f("ix_users_customer_id"), "users", ["customer_id"], unique=False)
    op.create_foreign_key(
        "fk_users_customer_id_customers",
        "users",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_customer_id_customers", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_customer_id"), table_name="users")
    op.drop_column("users", "customer_id")
    op.drop_constraint("ck_users_valid_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_valid_role",
        "users",
        "role IN ('manager', 'warehouse')",
    )
