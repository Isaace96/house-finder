from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_id
from app.database import get_session
from app.models import Property, PropertyStatus, Search, SearchProperty
from app.schemas import CountsOut, PreviewOut, PropertyOut, StatusUpdate
from app.services.preview import fetch_preview

router = APIRouter(prefix="/api", tags=["properties"])

BASE_URL = "https://www.rightmove.co.uk"
SORT_OPTIONS = {
    "price_per_sqm_asc": (Property.price_per_sqm.asc().nullslast(),),
    "price_per_sqm_desc": (Property.price_per_sqm.desc().nullslast(),),
    "price_asc": (Property.price.asc().nullslast(),),
    "price_desc": (Property.price.desc().nullslast(),),
    "sqm_desc": (Property.sqm.desc().nullslast(),),
}


async def _ensure_search_owned(session: AsyncSession, search_id: int, user_id: UUID) -> Search:
    search = await session.get(Search, search_id)
    if not search or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")
    return search


@router.get("/searches/{search_id}/properties", response_model=list[PropertyOut])
async def list_properties(
    search_id: int,
    status: Literal["unreviewed", "shortlisted", "rejected"] | None = None,
    sort: str = "price_per_sqm_asc",
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    search = await _ensure_search_owned(session, search_id, user_id)

    effective_status = func.coalesce(PropertyStatus.status, "unreviewed")

    stmt = (
        select(Property, effective_status.label("effective_status"))
        .join(SearchProperty, SearchProperty.property_id == Property.id)
        .outerjoin(
            PropertyStatus,
            (PropertyStatus.property_id == Property.id)
            & (PropertyStatus.user_id == user_id),
        )
        .where(
            SearchProperty.search_id == search_id,
            Property.sqm.is_not(None),
            Property.sqm > search.sqm_min,
            Property.sqm < search.sqm_max,
            Property.property_listing_type == search.search_type,
        )
    )
    if status:
        stmt = stmt.where(effective_status == status)

    order = SORT_OPTIONS.get(sort, SORT_OPTIONS["price_per_sqm_asc"])
    stmt = stmt.order_by(*order)

    result = await session.execute(stmt)
    rows = result.all()
    return [
        PropertyOut(
            id=p.id,
            rightmove_id=p.rightmove_id,
            link=p.link,
            full_url=f"{BASE_URL}{p.link}",
            sqm=p.sqm,
            price=p.price,
            price_per_sqm=p.price_per_sqm,
            address=p.address,
            property_listing_type=p.property_listing_type,
            status=eff,
        )
        for p, eff in rows
    ]


@router.get("/searches/{search_id}/counts", response_model=CountsOut)
async def get_counts(
    search_id: int,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    search = await _ensure_search_owned(session, search_id, user_id)

    effective_status = func.coalesce(PropertyStatus.status, "unreviewed")

    stmt = (
        select(effective_status.label("s"), func.count().label("c"))
        .select_from(Property)
        .join(SearchProperty, SearchProperty.property_id == Property.id)
        .outerjoin(
            PropertyStatus,
            (PropertyStatus.property_id == Property.id)
            & (PropertyStatus.user_id == user_id),
        )
        .where(
            SearchProperty.search_id == search_id,
            Property.sqm.is_not(None),
            Property.sqm > search.sqm_min,
            Property.sqm < search.sqm_max,
            Property.property_listing_type == search.search_type,
        )
        .group_by(effective_status)
    )
    result = await session.execute(stmt)
    counts = {"unreviewed": 0, "shortlisted": 0, "rejected": 0}
    for s, c in result.all():
        if s in counts:
            counts[s] = c
    return CountsOut(**counts)


@router.put("/properties/{rightmove_id}/status", status_code=204)
async def set_status(
    rightmove_id: int,
    body: StatusUpdate,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    prop = await session.execute(
        select(Property.id).where(Property.rightmove_id == rightmove_id)
    )
    prop_id = prop.scalar_one_or_none()
    if prop_id is None:
        raise HTTPException(status_code=404, detail="Property not found")

    stmt = (
        pg_insert(PropertyStatus)
        .values(user_id=user_id, property_id=prop_id, status=body.status)
        .on_conflict_do_update(
            index_elements=["user_id", "property_id"],
            set_={"status": body.status},
        )
    )
    await session.execute(stmt)
    await session.commit()


@router.get("/properties/{rightmove_id}/preview", response_model=PreviewOut)
async def get_preview(
    rightmove_id: int,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    import asyncio

    prop = await session.execute(
        select(Property).where(Property.rightmove_id == rightmove_id)
    )
    prop = prop.scalar_one_or_none()
    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")

    if prop.preview_data:
        return PreviewOut(**prop.preview_data)

    try:
        payload = await asyncio.to_thread(
            fetch_preview,
            rightmove_id,
            prop.link,
            prop.sqm,
            prop.price,
            prop.price_per_sqm,
            prop.address,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Preview fetch failed: {e}") from e

    prop.preview_data = payload
    prop.preview_fetched_at = datetime.now(timezone.utc)
    await session.commit()

    return PreviewOut(**payload)
