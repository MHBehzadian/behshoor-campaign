"""SQLAlchemy models for the Zanjan campaign system.

Shop.status is the single source of truth for where a shop sits in its
lifecycle (see CLAUDE.md / the campaign-logic artifact for the full state
machine). Everything else (PackDelivery, FollowUpAttempt, OrderFulfillment,
CheckupVisit) is an append-only event log that status transitions are
derived from.
"""
from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SCOUT = "scout"          # در‌آور — Telegram bot only
    VISITOR = "visitor"      # ویزیتور — website
    DISTRIBUTOR = "distributor"  # پخش — website


class ShopStatus(str, enum.Enum):
    """PACK_DELIVERED doubles as "awaiting order-1 follow-up" and ORDER1_DONE
    doubles as "awaiting order-2 follow-up" — there is no separate actor
    between those pairs of events, so no separate QUEUED_FOLLOWUP_* status
    exists. A rejected follow-up attempt just leaves the shop in the same
    status; it resurfaces once FollowUpAttempt.rescheduled_to has passed."""

    REGISTERED = "registered"
    AWAITING_THRESHOLD = "awaiting_threshold"   # score below current admin threshold
    QUEUED_FOR_PACK = "queued_for_pack"
    PACK_DELIVERED = "pack_delivered"            # awaiting order-1 follow-up
    ORDER1_PENDING_DELIVERY = "order1_pending_delivery"
    ORDER1_DONE = "order1_done"                  # awaiting order-2 follow-up
    ORDER2_PENDING_DELIVERY = "order2_pending_delivery"
    STEADY_CUSTOMER = "steady_customer"
    DROPPED = "dropped"      # manually removed from follow-up by admin


class FollowUpOutcome(str, enum.Enum):
    PENDING = "pending"
    REJECTED = "rejected"
    CLOSED = "closed"


class DayType(str, enum.Enum):
    DISTRIBUTION = "distribution"
    FOLLOWUP = "followup"
    HOLIDAY = "holiday"


class CheckupMethod(str, enum.Enum):
    IN_PERSON = "in_person"
    PHONE = "phone"


class CommissionRole(str, enum.Enum):
    SCOUT = "scout"
    VISITOR = "visitor"
    DISTRIBUTOR = "distributor"


# --------------------------------------------------------------------------
# Core tables
# --------------------------------------------------------------------------

class Region(Base):
    """One of Zanjan's 20 areas. Boundary is user-drawn on the map (phase 3);
    nullable until then, and always re-editable."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    reference_photo_url: Mapped[str | None] = mapped_column(String(500))
    boundary_geojson: Mapped[dict | None] = mapped_column(JSON)  # GeoJSON Polygon
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shops: Mapped[list["Shop"]] = relationship(back_populates="region")


class User(Base):
    """A person in the system. telegram_id is set only for scouts (bot login);
    username/password_hash is set only for admin/visitor/distributor (website login)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(32))

    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))

    # Only meaningful for role == VISITOR when the second sub-team is enabled.
    visitor_subteam: Mapped[int | None] = mapped_column()

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"))
    registered_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    name: Mapped[str] = mapped_column(String(200))
    address_text: Mapped[str] = mapped_column(Text)
    photo_url: Mapped[str] = mapped_column(String(500))
    scout_score: Mapped[int] = mapped_column()  # 1-3, set by scout at registration
    location_lat: Mapped[float] = mapped_column()
    location_lng: Mapped[float] = mapped_column()

    status: Mapped[ShopStatus] = mapped_column(
        Enum(ShopStatus, native_enum=False), default=ShopStatus.REGISTERED
    )
    # Which visitor sub-team (1 or 2) this shop was assigned to for pack delivery.
    assigned_subteam: Mapped[int | None] = mapped_column()

    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    editable_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    region: Mapped["Region"] = relationship(back_populates="shops")
    pack_deliveries: Mapped[list["PackDelivery"]] = relationship(back_populates="shop")
    followup_attempts: Mapped[list["FollowUpAttempt"]] = relationship(back_populates="shop")
    order_fulfillments: Mapped[list["OrderFulfillment"]] = relationship(back_populates="shop")
    checkup_visits: Mapped[list["CheckupVisit"]] = relationship(back_populates="shop")
    phones: Mapped[list["ShopPhone"]] = relationship(back_populates="shop")


class ShopPhone(Base):
    """A phone number anyone on staff picked up for a shop, with a short note
    (whose number it is, when to call, etc). A shop can have several — no one
    person owns "the" phone number, so this is append-only, not a single
    editable field."""

    __tablename__ = "shop_phones"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    added_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    phone: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shop: Mapped["Shop"] = relationship(back_populates="phones")


class DaySchedule(Base):
    """What kind of day a given calendar date is. Freely reassignable by the
    admin (days can be swapped), including marking a day as a holiday."""

    __tablename__ = "day_schedules"
    __table_args__ = (UniqueConstraint("date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    day_type: Mapped[DayType] = mapped_column(Enum(DayType, native_enum=False))
    target_region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id"))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PackDelivery(Base):
    """Visitor's first touch: delivers the free promo pack, days 1-3 of the
    shop's lifecycle."""

    __tablename__ = "pack_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    visitor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    opinion_text: Mapped[str | None] = mapped_column(Text)
    voice_note_url: Mapped[str | None] = mapped_column(String(500))
    score_1_5: Mapped[int] = mapped_column()

    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shop: Mapped["Shop"] = relationship(back_populates="pack_deliveries")


class FollowUpAttempt(Base):
    """One visit/call by the visitor trying to close order 1 or order 2.
    Repeats with no cap until closed or the admin drops the shop."""

    __tablename__ = "followup_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    visitor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    order_number: Mapped[int] = mapped_column()  # 1 or 2

    outcome: Mapped[FollowUpOutcome] = mapped_column(
        Enum(FollowUpOutcome, native_enum=False), default=FollowUpOutcome.PENDING
    )
    reject_reason: Mapped[str | None] = mapped_column(Text)
    rescheduled_to: Mapped[date | None] = mapped_column(Date)
    product_name: Mapped[str | None] = mapped_column(String(200))  # free text, filled when closed — no price catalog

    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shop: Mapped["Shop"] = relationship(back_populates="followup_attempts")


class OrderFulfillment(Base):
    """The distributor's physical delivery + cash collection for an order the
    visitor closed. `amount` here is the final source of truth for both the
    visitor's 8% and the distributor's 3% commission — it overrides whatever
    the visitor logged in FollowUpAttempt if they differ."""

    __tablename__ = "order_fulfillments"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    distributor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    followup_attempt_id: Mapped[int | None] = mapped_column(ForeignKey("followup_attempts.id"))

    order_number: Mapped[int | None] = mapped_column()  # 1, 2, or None for a later recurring order
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    shop: Mapped["Shop"] = relationship(back_populates="order_fulfillments")


class CheckupVisit(Base):
    """Weekly scheduled check-up with a steady customer (after order 2),
    handled solely by the distributor — in person or by phone."""

    __tablename__ = "checkup_visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    distributor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    scheduled_for: Mapped[date] = mapped_column(Date)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    method: Mapped[CheckupMethod | None] = mapped_column(Enum(CheckupMethod, native_enum=False))
    notes: Mapped[str | None] = mapped_column(Text)
    resulted_order_id: Mapped[int | None] = mapped_column(ForeignKey("order_fulfillments.id"))

    shop: Mapped["Shop"] = relationship(back_populates="checkup_visits")


class CommissionLedger(Base):
    """Append-only computed commission entries, for the accounting dashboard.
    One row per payable event (a shop registration, an order fulfillment)."""

    __tablename__ = "commission_ledger"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    order_fulfillment_id: Mapped[int | None] = mapped_column(ForeignKey("order_fulfillments.id"))
    role: Mapped[CommissionRole] = mapped_column(Enum(CommissionRole, native_enum=False))
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Settings(Base):
    """Single-row table of admin-tunable global settings."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    score_threshold: Mapped[int] = mapped_column(default=3)  # only shops with scout_score >= this get packs
    visitor_dual_team_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    scout_fixed_fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    visitor_fixed_fee: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    visitor_commission_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=8)
    distributor_commission_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=3)
    checkup_interval_days: Mapped[int] = mapped_column(default=7)
