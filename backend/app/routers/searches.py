import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_id
from app.database import get_session
from app.models import Search
from app.schemas import SearchCreate, SearchOut
from app.tasks.scrape_task import run_scrape

router = APIRouter(prefix="/api/searches", tags=["searches"])


@router.get("", response_model=list[SearchOut])
async def list_searches(
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Search)
        .where(Search.user_id == user_id)
        .order_by(Search.created_at.desc())
    )
    return list(result.scalars())


@router.post("", response_model=SearchOut, status_code=status.HTTP_201_CREATED)
async def create_search(
    body: SearchCreate,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    search = Search(
        user_id=user_id,
        query_url=body.query_url,
        search_type=body.search_type,
        label=body.label,
        sqm_min=body.sqm_min,
        sqm_max=body.sqm_max,
        max_pages=body.max_pages,
        status="pending",
        progress=0,
    )
    session.add(search)
    await session.commit()
    await session.refresh(search)

    asyncio.create_task(run_scrape(search.id, user_id))
    return search


@router.get("/{search_id}", response_model=SearchOut)
async def get_search(
    search_id: int,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    search = await session.get(Search, search_id)
    if not search or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")
    return search


@router.delete("/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(
    search_id: int,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    search = await session.get(Search, search_id)
    if not search or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")
    await session.execute(delete(Search).where(Search.id == search_id))
    await session.commit()


@router.post("/{search_id}/rerun", response_model=SearchOut)
async def rerun_search(
    search_id: int,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    search = await session.get(Search, search_id)
    if not search or search.user_id != user_id:
        raise HTTPException(status_code=404, detail="Search not found")
    if search.status in ("pending", "scraping"):
        raise HTTPException(status_code=409, detail="Search is already running")

    search.status = "pending"
    search.progress = 0
    search.error_message = None
    search.total_found = 0
    search.total_failed = 0
    await session.commit()
    await session.refresh(search)

    asyncio.create_task(run_scrape(search.id, user_id))
    return search
