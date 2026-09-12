"""The shop state machine + commission bookkeeping. This is the one place
that moves a Shop from one ShopStatus to the next — the FastAPI routers stay
thin and call into here.

State machine (see the campaign-logic artifact linked from CLAUDE.md):
    REGISTERED -> AWAITING_THRESHOLD | QUEUED_FOR_PACK
    QUEUED_FOR_PACK -> PACK_DELIVERED                 [visitor delivers the pack]
    PACK_DELIVERED  -> (rejected follow-up: stays, resurfaces at rescheduled_to)
                    -> ORDER1_PENDING_DELIVERY -> ORDER1_DONE   [distributor fulfills]
    ORDER1_DONE     -> (same reject loop, now order 2)
                    -> ORDER2_PENDING_DELIVERY -> STEADY_CUSTOMER   [distributor fulfills]
    STEADY_CUSTOMER -> recurring CheckupVisit rows, distributor-only from here on

PACK_DELIVERED and ORDER1_DONE double as "awaiting the next follow-up round" —
there's no separate actor between delivery/fulfillment and becoming
eligible for follow-up, so no separate QUEUED_FOLLOWUP_* status exists.
"""
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CheckupMethod,
    CheckupVisit,
    CommissionLedger,
    CommissionRole,
    DaySchedule,
    DayType,
    FollowUpAttempt,
    FollowUpOutcome,
    OrderFulfillment,
    PackDelivery,
    Region,
    Shop,
    ShopStatus,
)
from app.services.common import get_settings
from app.timeutil import today_local

DEFAULT_FOLLOWUP_RESCHEDULE_DAYS = 3


# --------------------------------------------------------------------------
# Region targeting
# --------------------------------------------------------------------------

async def get_todays_distribution_region(session: AsyncSession) -> Region | None:
    """The region visitors deliver packs to *today* — a DaySchedule row dated
    today with day_type == DISTRIBUTION. (Different from the bot's
    "get_active_region", which looks one day ahead for scouts.)"""
    today = today_local()
    result = await session.execute(
        select(DaySchedule).where(DaySchedule.date == today, DaySchedule.day_type == DayType.DISTRIBUTION)
    )
    schedule = result.scalar_one_or_none()
    if schedule is None or schedule.target_region_id is None:
        return None
    return await session.get(Region, schedule.target_region_id)


# --------------------------------------------------------------------------
# Commission ledger
# --------------------------------------------------------------------------

async def _record_commission(
    session: AsyncSession,
    *,
    user_id: int,
    shop_id: int,
    role: CommissionRole,
    amount: float,
    order_fulfillment_id: int | None = None,
) -> None:
    if amount <= 0:
        return
    session.add(
        CommissionLedger(
            user_id=user_id,
            shop_id=shop_id,
            order_fulfillment_id=order_fulfillment_id,
            role=role,
            amount=amount,
        )
    )


async def record_scout_commission(session: AsyncSession, shop: Shop) -> None:
    settings = await get_settings(session)
    await _record_commission(
        session,
        user_id=shop.registered_by_id,
        shop_id=shop.id,
        role=CommissionRole.SCOUT,
        amount=float(settings.scout_fixed_fee),
    )
    await session.commit()


# --------------------------------------------------------------------------
# Pack delivery (visitor, days the admin marks DISTRIBUTION)
# --------------------------------------------------------------------------

async def get_pack_queue(session: AsyncSession, subteam: int | None) -> list[Shop]:
    """Shops ready for pack delivery in today's target region, split 50/50 by
    registration order across the two visitor sub-teams if enabled. The split
    is recomputed (and persisted onto Shop.assigned_subteam) on every call, so
    an emergency address added mid-morning is picked up immediately."""
    region = await get_todays_distribution_region(session)
    if region is None:
        return []

    settings = await get_settings(session)
    result = await session.execute(
        select(Shop)
        .where(Shop.region_id == region.id, Shop.status == ShopStatus.QUEUED_FOR_PACK)
        .order_by(Shop.registered_at.asc())
    )
    shops = list(result.scalars().all())

    if settings.visitor_dual_team_enabled:
        half = (len(shops) + 1) // 2  # first (larger) half to sub-team 1
        for i, shop in enumerate(shops):
            shop.assigned_subteam = 1 if i < half else 2
        await session.commit()
        if subteam is not None:
            shops = [s for s in shops if s.assigned_subteam == subteam]
    else:
        for shop in shops:
            shop.assigned_subteam = None
        await session.commit()

    return shops


async def register_pack_delivery(
    session: AsyncSession,
    *,
    shop_id: int,
    visitor_id: int,
    opinion_text: str | None,
    voice_note_url: str | None,
    score_1_5: int,
) -> PackDelivery:
    shop = await session.get(Shop, shop_id)
    if shop is None or shop.status != ShopStatus.QUEUED_FOR_PACK:
        raise ValueError("این مغازه در صف پخش پک نیست.")

    delivery = PackDelivery(
        shop_id=shop_id,
        visitor_id=visitor_id,
        opinion_text=opinion_text,
        voice_note_url=voice_note_url,
        score_1_5=score_1_5,
    )
    session.add(delivery)

    settings = await get_settings(session)
    await _record_commission(
        session,
        user_id=visitor_id,
        shop_id=shop_id,
        role=CommissionRole.VISITOR,
        amount=float(settings.visitor_fixed_fee),
    )

    # No artificial cool-down in the data model — admin's own day-scheduling
    # (marking a FOLLOWUP day a few days later) provides the real-world gap.
    shop.status = ShopStatus.PACK_DELIVERED
    await session.commit()
    await session.refresh(delivery)
    return delivery


# --------------------------------------------------------------------------
# Follow-up (visitor, days the admin marks FOLLOWUP)
# --------------------------------------------------------------------------

_FOLLOWUP_STATUS_BY_ORDER = {
    1: ShopStatus.PACK_DELIVERED,
    2: ShopStatus.ORDER1_DONE,
}
_PENDING_DELIVERY_STATUS_BY_ORDER = {
    1: ShopStatus.ORDER1_PENDING_DELIVERY,
    2: ShopStatus.ORDER2_PENDING_DELIVERY,
}


def _order_number_for_status(status: ShopStatus) -> int | None:
    for order_number, s in _FOLLOWUP_STATUS_BY_ORDER.items():
        if s == status:
            return order_number
    return None


async def get_followup_queue(session: AsyncSession) -> list[Shop]:
    """Shops due for a follow-up visit today: awaiting order 1 or order 2,
    and not waiting on a future reschedule date."""
    today = today_local()
    result = await session.execute(
        select(Shop)
        .where(
            Shop.status.in_([ShopStatus.PACK_DELIVERED, ShopStatus.ORDER1_DONE]),
        )
        .order_by(Shop.registered_at.asc())
    )
    shops = list(result.scalars().all())

    due = []
    for shop in shops:
        latest = await _latest_open_attempt(session, shop.id)
        if latest is None or latest.rescheduled_to is None or latest.rescheduled_to <= today:
            due.append(shop)
    return due


async def _latest_open_attempt(session: AsyncSession, shop_id: int) -> FollowUpAttempt | None:
    result = await session.execute(
        select(FollowUpAttempt)
        .where(FollowUpAttempt.shop_id == shop_id, FollowUpAttempt.outcome == FollowUpOutcome.REJECTED)
        .order_by(FollowUpAttempt.attempted_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def register_followup_attempt(
    session: AsyncSession,
    *,
    shop_id: int,
    visitor_id: int,
    closed: bool,
    product_name: str | None = None,
    reject_reason: str | None = None,
    rescheduled_to: date | None = None,
) -> FollowUpAttempt:
    shop = await session.get(Shop, shop_id)
    if shop is None:
        raise ValueError("مغازه پیدا نشد.")
    order_number = _order_number_for_status(shop.status)
    if order_number is None:
        raise ValueError("این مغازه در صف پیگیری نیست.")

    attempt = FollowUpAttempt(
        shop_id=shop_id,
        visitor_id=visitor_id,
        order_number=order_number,
        outcome=FollowUpOutcome.CLOSED if closed else FollowUpOutcome.REJECTED,
        reject_reason=None if closed else reject_reason,
        rescheduled_to=None if closed else (rescheduled_to or today_local() + timedelta(days=DEFAULT_FOLLOWUP_RESCHEDULE_DAYS)),
        product_name=product_name if closed else None,
    )
    session.add(attempt)

    if closed:
        shop.status = _PENDING_DELIVERY_STATUS_BY_ORDER[order_number]
    # if rejected, shop.status is left as-is (still queued) — it resurfaces via
    # get_followup_queue() once rescheduled_to has passed. Admin can always
    # drop it permanently by setting Shop.status = DROPPED separately.

    await session.commit()
    await session.refresh(attempt)
    return attempt


# --------------------------------------------------------------------------
# Order fulfillment (distributor) — the source of truth for commission amounts
# --------------------------------------------------------------------------

async def get_fulfillment_queue(session: AsyncSession) -> list[Shop]:
    result = await session.execute(
        select(Shop)
        .where(Shop.status.in_([ShopStatus.ORDER1_PENDING_DELIVERY, ShopStatus.ORDER2_PENDING_DELIVERY]))
        .order_by(Shop.registered_at.asc())
    )
    return list(result.scalars().all())


async def register_order_fulfillment(
    session: AsyncSession,
    *,
    shop_id: int,
    distributor_id: int,
    amount: float,
    notes: str | None = None,
) -> OrderFulfillment:
    shop = await session.get(Shop, shop_id)
    if shop is None:
        raise ValueError("مغازه پیدا نشد.")
    order_number = None
    for n, s in _PENDING_DELIVERY_STATUS_BY_ORDER.items():
        if s == shop.status:
            order_number = n
            break
    if order_number is None:
        raise ValueError("این مغازه منتظر تحویل سفارش نیست.")

    result = await session.execute(
        select(FollowUpAttempt)
        .where(
            FollowUpAttempt.shop_id == shop_id,
            FollowUpAttempt.order_number == order_number,
            FollowUpAttempt.outcome == FollowUpOutcome.CLOSED,
        )
        .order_by(FollowUpAttempt.attempted_at.desc())
        .limit(1)
    )
    attempt = result.scalar_one_or_none()

    fulfillment = OrderFulfillment(
        shop_id=shop_id,
        distributor_id=distributor_id,
        followup_attempt_id=attempt.id if attempt else None,
        order_number=order_number,
        amount=amount,
        notes=notes,
    )
    session.add(fulfillment)
    await session.flush()

    settings = await get_settings(session)
    await _record_commission(
        session,
        user_id=distributor_id,
        shop_id=shop_id,
        role=CommissionRole.DISTRIBUTOR,
        amount=amount * float(settings.distributor_commission_pct) / 100,
        order_fulfillment_id=fulfillment.id,
    )
    if attempt is not None:
        await _record_commission(
            session,
            user_id=attempt.visitor_id,
            shop_id=shop_id,
            role=CommissionRole.VISITOR,
            amount=amount * float(settings.visitor_commission_pct) / 100,
            order_fulfillment_id=fulfillment.id,
        )

    if order_number == 1:
        shop.status = ShopStatus.ORDER1_DONE  # doubles as "awaiting order-2 follow-up"
    else:
        shop.status = ShopStatus.STEADY_CUSTOMER
        await _schedule_next_checkup(session, shop, distributor_id, base_date=today_local())

    await session.commit()
    await session.refresh(fulfillment)
    return fulfillment


# --------------------------------------------------------------------------
# Weekly check-ups (distributor only, after the shop is a steady customer)
# --------------------------------------------------------------------------

async def _schedule_next_checkup(
    session: AsyncSession, shop: Shop, distributor_id: int, *, base_date: date
) -> CheckupVisit:
    settings = await get_settings(session)
    checkup = CheckupVisit(
        shop_id=shop.id,
        distributor_id=distributor_id,
        scheduled_for=base_date + timedelta(days=settings.checkup_interval_days),
    )
    session.add(checkup)
    await session.flush()
    return checkup


async def get_checkup_queue(session: AsyncSession, distributor_id: int) -> list[CheckupVisit]:
    today = today_local()
    result = await session.execute(
        select(CheckupVisit)
        .where(
            CheckupVisit.distributor_id == distributor_id,
            CheckupVisit.done_at.is_(None),
            CheckupVisit.scheduled_for <= today,
        )
        .order_by(CheckupVisit.scheduled_for.asc())
    )
    return list(result.scalars().all())


async def complete_checkup(
    session: AsyncSession,
    *,
    checkup_id: int,
    distributor_id: int,
    method: CheckupMethod,
    notes: str | None = None,
    resulted_order_amount: float | None = None,
) -> CheckupVisit:
    checkup = await session.get(CheckupVisit, checkup_id)
    if checkup is None or checkup.distributor_id != distributor_id:
        raise ValueError("این سرکشی پیدا نشد.")

    checkup.done_at = datetime.now()
    checkup.method = method
    checkup.notes = notes

    shop = await session.get(Shop, checkup.shop_id)

    if resulted_order_amount is not None:
        fulfillment = OrderFulfillment(
            shop_id=checkup.shop_id,
            distributor_id=distributor_id,
            order_number=None,
            amount=resulted_order_amount,
            notes="سفارش حاصل از سرکشی هفتگی",
        )
        session.add(fulfillment)
        await session.flush()
        checkup.resulted_order_id = fulfillment.id

        settings = await get_settings(session)
        await _record_commission(
            session,
            user_id=distributor_id,
            shop_id=checkup.shop_id,
            role=CommissionRole.DISTRIBUTOR,
            amount=resulted_order_amount * float(settings.distributor_commission_pct) / 100,
            order_fulfillment_id=fulfillment.id,
        )
        # No visitor cut here — reorders after order 2 are distributor-only.

    await _schedule_next_checkup(session, shop, distributor_id, base_date=today_local())

    await session.commit()
    await session.refresh(checkup)
    return checkup
