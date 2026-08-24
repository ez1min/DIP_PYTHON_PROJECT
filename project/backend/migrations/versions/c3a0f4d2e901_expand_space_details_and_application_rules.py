"""expand space details and application rules

Revision ID: c3a0f4d2e901
Revises: f778bb38a150
Create Date: 2026-08-22 14:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3a0f4d2e901"
down_revision: Union[str, Sequence[str], None] = "f778bb38a150"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("spaces", sa.Column("floor", sa.String(length=100), nullable=True))
    op.add_column("spaces", sa.Column("building_structure", sa.String(length=150), nullable=True))
    op.add_column("spaces", sa.Column("remodeling_status", sa.String(length=30), nullable=True))
    op.add_column("spaces", sa.Column("remodeling_support", sa.Text(), nullable=True))
    op.add_column("spaces", sa.Column("managing_agency", sa.String(length=200), nullable=True))
    op.add_column("spaces", sa.Column("agency_contact", sa.String(length=50), nullable=True))
    op.add_column("spaces", sa.Column("transport_info", sa.Text(), nullable=True))
    op.add_column(
        "spaces", sa.Column("utilities", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
    )
    op.add_column(
        "spaces", sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
    )
    op.add_column(
        "spaces", sa.Column("features", sa.JSON(), nullable=False, server_default=sa.text("'[]'"))
    )
    op.add_column("spaces", sa.Column("available_from", sa.Date(), nullable=True))
    op.add_column("spaces", sa.Column("source_name", sa.String(length=200), nullable=True))
    op.add_column("spaces", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("spaces", sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_constraint("uq_application_visit", "applications", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_application_visit", "applications", ["user_id", "space_id", "visit_date"]
    )
    op.drop_column("spaces", "source_updated_at")
    op.drop_column("spaces", "source_url")
    op.drop_column("spaces", "source_name")
    op.drop_column("spaces", "available_from")
    op.drop_column("spaces", "features")
    op.drop_column("spaces", "tags")
    op.drop_column("spaces", "utilities")
    op.drop_column("spaces", "transport_info")
    op.drop_column("spaces", "agency_contact")
    op.drop_column("spaces", "managing_agency")
    op.drop_column("spaces", "remodeling_support")
    op.drop_column("spaces", "remodeling_status")
    op.drop_column("spaces", "building_structure")
    op.drop_column("spaces", "floor")
