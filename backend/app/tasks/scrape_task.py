import asyncio
import contextlib
import os
from uuid import UUID

import requests
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import SessionLocal
from app.models import Property, Search, SearchProperty
from app.services.scraper import (
    PROPERTIES_PER_PAGE,
    extract_data_from_properties_link,
    fetch_property_links_for_page,
    rightmove_id_from_link,
)

_user_locks: dict[UUID, asyncio.Lock] = {}

KEEP_ALIVE_INTERVAL_SECONDS = 8 * 60


async def _keep_alive_ping(search_id: int) -> None:
    external_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not external_url:
        return
    ping_url = f"{external_url.rstrip('/')}/api/health"
    while True:
        await asyncio.sleep(KEEP_ALIVE_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(requests.get, ping_url, timeout=10)
            logger.debug(f"Search {search_id}: keep-alive ping ok")
        except Exception as e:
            logger.warning(f"Search {search_id}: keep-alive ping failed: {e}")


def _lock_for(user_id: UUID) -> asyncio.Lock:
    lock = _user_locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _user_locks[user_id] = lock
    return lock


async def _upsert_property(session, details) -> int | None:
    rm_id = rightmove_id_from_link(details.link)
    if rm_id is None:
        return None

    stmt = (
        pg_insert(Property)
        .values(
            rightmove_id=rm_id,
            link=details.link,
            sqm=details.sqm,
            price=details.price,
            price_per_sqm=details.price_per_sqm,
            address=details.address,
            property_listing_type=details.property_listing_type,
        )
        .on_conflict_do_update(
            index_elements=["rightmove_id"],
            set_={
                "sqm": details.sqm,
                "price": details.price,
                "price_per_sqm": details.price_per_sqm,
                "address": details.address,
                "property_listing_type": details.property_listing_type,
            },
        )
        .returning(Property.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def _set_progress(search_id: int, progress: int, status: str | None = None):
    async with SessionLocal() as session:
        values = {"progress": progress}
        if status is not None:
            values["status"] = status
        await session.execute(
            update(Search).where(Search.id == search_id).values(**values)
        )
        await session.commit()


async def run_scrape(search_id: int, user_id: UUID) -> None:
    lock = _lock_for(user_id)
    if lock.locked():
        async with SessionLocal() as session:
            await session.execute(
                update(Search)
                .where(Search.id == search_id)
                .values(
                    status="failed",
                    error_message="Another scrape is already running for this user",
                )
            )
            await session.commit()
        return

    async with lock:
        async with SessionLocal() as session:
            search = await session.get(Search, search_id)
            if not search:
                return
            query_url = search.query_url
            search_type = search.search_type
            max_pages = search.max_pages
            search.status = "scraping"
            search.progress = 1
            await session.commit()

        ping_task = asyncio.create_task(_keep_alive_ping(search_id))
        try:
            total_found = 0
            total_failed = 0
            seen_links: set[str] = set()
            for page_index in range(max_pages):
                logger.info(f"Search {search_id}: page {page_index + 1}/{max_pages}")
                offset = page_index * PROPERTIES_PER_PAGE
                try:
                    links = await asyncio.to_thread(
                        fetch_property_links_for_page, query_url, offset
                    )
                except Exception as e:
                    logger.warning(
                        f"Search {search_id}: listing page {page_index + 1} failed after retries: {e}"
                    )
                    total_failed += 1
                    continue
                if not links:
                    break

                for link in links:
                    if link in seen_links:
                        continue
                    seen_links.add(link)

                    rm_id = rightmove_id_from_link(link)
                    if rm_id is None:
                        continue

                    try:
                        async with SessionLocal() as session:
                            existing = await session.execute(
                                select(Property).where(Property.rightmove_id == rm_id)
                            )
                            prop = existing.scalar_one_or_none()

                            if prop is None:
                                details = await asyncio.to_thread(
                                    extract_data_from_properties_link, link, search_type
                                )
                                if details is None:
                                    total_failed += 1
                                    continue
                                prop_id = await _upsert_property(session, details)
                            else:
                                prop_id = prop.id

                            if prop_id is not None:
                                await session.execute(
                                    pg_insert(SearchProperty)
                                    .values(search_id=search_id, property_id=prop_id)
                                    .on_conflict_do_nothing()
                                )
                                total_found += 1
                            await session.commit()
                    except Exception as e:
                        logger.warning(f"Search {search_id}: listing {link} failed: {e}")
                        total_failed += 1
                        continue

                progress = min(99, int(((page_index + 1) / max_pages) * 100))
                await _set_progress(search_id, progress)

            async with SessionLocal() as session:
                await session.execute(
                    update(Search)
                    .where(Search.id == search_id)
                    .values(
                        status="complete",
                        progress=100,
                        total_found=total_found,
                        total_failed=total_failed,
                    )
                )
                await session.commit()
        except Exception as e:
            logger.exception(f"Search {search_id} failed: {e}")
            async with SessionLocal() as session:
                await session.execute(
                    update(Search)
                    .where(Search.id == search_id)
                    .values(status="failed", error_message=str(e)[:500])
                )
                await session.commit()
        finally:
            ping_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ping_task
