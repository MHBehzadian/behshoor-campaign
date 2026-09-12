from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import CheckupMethod, DayType, ShopStatus, UserRole

# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    full_name: str
    visitor_subteam: int | None = None


# --------------------------------------------------------------------------
# Regions
# --------------------------------------------------------------------------

class RegionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    reference_photo_url: str | None
    boundary_geojson: dict | None


class RegionCreate(BaseModel):
    name: str
    reference_photo_url: str | None = None
    boundary_geojson: dict | None = None


class RegionUpdate(BaseModel):
    name: str | None = None
    reference_photo_url: str | None = None
    boundary_geojson: dict | None = None  # re-editable any time, per the design decision


# --------------------------------------------------------------------------
# Day schedules
# --------------------------------------------------------------------------

class DayScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    day_type: DayType
    target_region_id: int | None


class DayScheduleSet(BaseModel):
    day_type: DayType
    target_region_id: int | None = None  # required when day_type == DISTRIBUTION


# --------------------------------------------------------------------------
# Shops (map / dashboard)
# --------------------------------------------------------------------------

class ShopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    region_id: int
    name: str
    address_text: str
    photo_url: str
    scout_score: int
    location_lat: float
    location_lng: float
    status: ShopStatus
    assigned_subteam: int | None
    registered_at: datetime


class ShopPhoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    note: str | None
    added_by_id: int
    created_at: datetime


class ShopPhoneCreate(BaseModel):
    phone: str
    note: str | None = None


# --------------------------------------------------------------------------
# Pack delivery (visitor)
# --------------------------------------------------------------------------

class PackDeliveryCreate(BaseModel):
    shop_id: int
    opinion_text: str | None = None
    voice_note_url: str | None = None
    score_1_5: int


# --------------------------------------------------------------------------
# Follow-up (visitor)
# --------------------------------------------------------------------------

class FollowUpAttemptCreate(BaseModel):
    shop_id: int
    closed: bool
    product_name: str | None = None       # required if closed
    reject_reason: str | None = None       # used if not closed
    rescheduled_to: date | None = None     # optional override; else default +3 days


# --------------------------------------------------------------------------
# Order fulfillment (distributor)
# --------------------------------------------------------------------------

class OrderFulfillmentCreate(BaseModel):
    shop_id: int
    amount: float
    notes: str | None = None


# --------------------------------------------------------------------------
# Check-ups (distributor)
# --------------------------------------------------------------------------

class CheckupVisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    scheduled_for: date


class CheckupComplete(BaseModel):
    method: CheckupMethod
    notes: str | None = None
    resulted_order_amount: float | None = None


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    score_threshold: int
    visitor_dual_team_enabled: bool
    scout_fixed_fee: float
    visitor_fixed_fee: float
    visitor_commission_pct: float
    distributor_commission_pct: float
    checkup_interval_days: int


class SettingsUpdate(BaseModel):
    score_threshold: int | None = None
    visitor_dual_team_enabled: bool | None = None
    scout_fixed_fee: float | None = None
    visitor_fixed_fee: float | None = None
    visitor_commission_pct: float | None = None
    distributor_commission_pct: float | None = None
    checkup_interval_days: int | None = None


# --------------------------------------------------------------------------
# Region stats (admin dashboard summary)
# --------------------------------------------------------------------------

class RegionStatsOut(BaseModel):
    region_id: int
    region_name: str
    total: int
    advertised: int
    in_followup: int
    order1_placed: int
    order2_placed: int
    steady_customer: int
    dropped: int


# --------------------------------------------------------------------------
# Commission report
# --------------------------------------------------------------------------

class CommissionEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    shop_id: int
    role: str
    amount: float
    computed_at: datetime


# --------------------------------------------------------------------------
# Users (admin managing scout/visitor/distributor accounts)
# --------------------------------------------------------------------------

class UserCreate(BaseModel):
    role: UserRole
    full_name: str
    phone: str | None = None
    telegram_id: int | None = None      # scouts
    username: str | None = None         # website login
    password: str | None = None         # website login
    visitor_subteam: int | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: UserRole
    full_name: str
    phone: str | None
    telegram_id: int | None
    username: str | None
    visitor_subteam: int | None
    is_active: bool
