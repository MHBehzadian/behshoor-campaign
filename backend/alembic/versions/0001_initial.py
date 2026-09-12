"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-11

Hand-written (no live DB to autogenerate against yet) — mirrors app/models.py.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.models import (
    CheckupMethod,
    CommissionRole,
    DayType,
    FollowUpOutcome,
    ShopStatus,
    UserRole,
)

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), unique=True, nullable=False),
        sa.Column("reference_photo_url", sa.String(500)),
        sa.Column("boundary_geojson", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("role", sa.Enum(UserRole, native_enum=False, name="userrole"), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("phone", sa.String(32)),
        sa.Column("telegram_id", sa.BigInteger, unique=True),
        sa.Column("username", sa.String(60), unique=True),
        sa.Column("password_hash", sa.String(255)),
        sa.Column("visitor_subteam", sa.Integer),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "shops",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("region_id", sa.Integer, sa.ForeignKey("regions.id"), nullable=False),
        sa.Column("registered_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address_text", sa.Text, nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=False),
        sa.Column("scout_score", sa.Integer, nullable=False),
        sa.Column("location_lat", sa.Float, nullable=False),
        sa.Column("location_lng", sa.Float, nullable=False),
        sa.Column(
            "status", sa.Enum(ShopStatus, native_enum=False, name="shopstatus"),
            nullable=False, server_default=ShopStatus.REGISTERED.value,
        ),
        sa.Column("assigned_subteam", sa.Integer),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("editable_until", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "shop_phones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("added_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("note", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "day_schedules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False, unique=True),
        sa.Column("day_type", sa.Enum(DayType, native_enum=False, name="daytype"), nullable=False),
        sa.Column("target_region_id", sa.Integer, sa.ForeignKey("regions.id")),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "pack_deliveries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("visitor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("opinion_text", sa.Text),
        sa.Column("voice_note_url", sa.String(500)),
        sa.Column("score_1_5", sa.Integer, nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "followup_attempts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("visitor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("order_number", sa.Integer, nullable=False),
        sa.Column(
            "outcome", sa.Enum(FollowUpOutcome, native_enum=False, name="followupoutcome"),
            nullable=False, server_default=FollowUpOutcome.PENDING.value,
        ),
        sa.Column("reject_reason", sa.Text),
        sa.Column("rescheduled_to", sa.Date),
        sa.Column("product_name", sa.String(200)),
        sa.Column("attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "order_fulfillments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("distributor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("followup_attempt_id", sa.Integer, sa.ForeignKey("followup_attempts.id")),
        sa.Column("order_number", sa.Integer),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("delivered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "checkup_visits",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("distributor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scheduled_for", sa.Date, nullable=False),
        sa.Column("done_at", sa.DateTime(timezone=True)),
        sa.Column("method", sa.Enum(CheckupMethod, native_enum=False, name="checkupmethod")),
        sa.Column("notes", sa.Text),
        sa.Column("resulted_order_id", sa.Integer, sa.ForeignKey("order_fulfillments.id")),
    )

    op.create_table(
        "commission_ledger",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("order_fulfillment_id", sa.Integer, sa.ForeignKey("order_fulfillments.id")),
        sa.Column("role", sa.Enum(CommissionRole, native_enum=False, name="commissionrole"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("score_threshold", sa.Integer, nullable=False, server_default="3"),
        sa.Column("visitor_dual_team_enabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("scout_fixed_fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("visitor_fixed_fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("visitor_commission_pct", sa.Numeric(5, 2), nullable=False, server_default="8"),
        sa.Column("distributor_commission_pct", sa.Numeric(5, 2), nullable=False, server_default="3"),
        sa.Column("checkup_interval_days", sa.Integer, nullable=False, server_default="7"),
    )
    op.execute("INSERT INTO settings (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("commission_ledger")
    op.drop_table("checkup_visits")
    op.drop_table("order_fulfillments")
    op.drop_table("followup_attempts")
    op.drop_table("pack_deliveries")
    op.drop_table("day_schedules")
    op.drop_table("shop_phones")
    op.drop_table("shops")
    op.drop_table("users")
    op.drop_table("regions")
