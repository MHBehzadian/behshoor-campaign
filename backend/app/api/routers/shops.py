import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SessionDep, require_admin, require_staff
from app.api.schemas import ShopOut, ShopPhoneCreate, ShopPhoneOut
from app.config import settings
from app.models import Shop, ShopPhone, ShopStatus, User

router = APIRouter(prefix="/shops", tags=["shops"])


@router.get("", response_model=list[ShopOut], dependencies=[Depends(require_staff)])
async def list_shops(
    region_id: int | None = None,
    status: ShopStatus | None = None,
    session: AsyncSession = SessionDep,
) -> list[Shop]:
    """Backs the admin map/dashboard: pins + status label per shop."""
    query = select(Shop)
    if region_id is not None:
        query = query.where(Shop.region_id == region_id)
    if status is not None:
        query = query.where(Shop.status == status)
    result = await session.execute(query.order_by(Shop.registered_at.desc()))
    return list(result.scalars().all())


@router.get("/{shop_id}", response_model=ShopOut, dependencies=[Depends(require_staff)])
async def get_shop(shop_id: int, session: AsyncSession = SessionDep) -> Shop:
    shop = await session.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(404, "مغازه پیدا نشد.")
    return shop


@router.get("/{shop_id}/photo", dependencies=[Depends(require_staff)])
async def get_shop_photo(shop_id: int, session: AsyncSession = SessionDep) -> Response:
    """Shop photos are Telegram file_ids (uploaded by the scout via the bot).
    Resolving them needs the bot token, so this proxies the bytes through our
    backend instead of ever handing the token to the browser."""
    shop = await session.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(404, "مغازه پیدا نشد.")

    async with httpx.AsyncClient() as client:
        meta = await client.get(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/getFile",
            params={"file_id": shop.photo_url},
        )
        meta.raise_for_status()
        file_path = meta.json()["result"]["file_path"]
        file_resp = await client.get(
            f"https://api.telegram.org/file/bot{settings.telegram_bot_token}/{file_path}"
        )
        file_resp.raise_for_status()

    return Response(
        content=file_resp.content,
        media_type=file_resp.headers.get("content-type", "image/jpeg"),
    )


@router.get("/{shop_id}/phones", response_model=list[ShopPhoneOut], dependencies=[Depends(require_staff)])
async def list_shop_phones(shop_id: int, session: AsyncSession = SessionDep) -> list[ShopPhone]:
    result = await session.execute(
        select(ShopPhone).where(ShopPhone.shop_id == shop_id).order_by(ShopPhone.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{shop_id}/phones", response_model=ShopPhoneOut)
async def add_shop_phone(
    shop_id: int,
    payload: ShopPhoneCreate,
    session: AsyncSession = SessionDep,
    user: User = Depends(require_staff),
) -> ShopPhone:
    """The scout bot never captures a phone number — anyone on staff (admin,
    visitor, or distributor) can add one from the field, each with its own
    short note, instead of a single admin-owned field."""
    shop = await session.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(404, "مغازه پیدا نشد.")
    entry = ShopPhone(shop_id=shop_id, phone=payload.phone, note=payload.note, added_by_id=user.id)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


@router.patch("/{shop_id}/drop", response_model=ShopOut, dependencies=[Depends(require_admin)])
async def drop_shop(shop_id: int, session: AsyncSession = SessionDep) -> Shop:
    """Admin manually pulling a shop out of the endless follow-up retry loop."""
    shop = await session.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(404, "مغازه پیدا نشد.")
    shop.status = ShopStatus.DROPPED
    await session.commit()
    await session.refresh(shop)
    return shop
