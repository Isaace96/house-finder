import asyncio
import contextlib
import gc
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
DETAIL_FETCH_CONCURRENCY = int(os.environ.get("SCRAPE_CONCURRENCY", "3"))


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
        semaphore = asyncio.Semaphore(DETAIL_FETCH_CONCURRENCY)

        async def fetch_detail(link: str):
            async with semaphore:
                return await asyncio.to_thread(
                    extract_data_from_properties_link, link, search_type
                )

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

                page_items: list[tuple[str, int]] = []
                for link in links:
                    if link in seen_links:
                        continue
                    seen_links.add(link)
                    rm_id = rightmove_id_from_link(link)
                    if rm_id is None:
                        continue
                    page_items.append((link, rm_id))

                if not page_items:
                    progress = min(99, int(((page_index + 1) / max_pages) * 100))
                    await _set_progress(search_id, progress)
                    continue

                async with SessionLocal() as session:
                    existing_result = await session.execute(
                        select(Property.rightmove_id, Property.id).where(
                            Property.rightmove_id.in_([rm for _, rm in page_items])
                        )
                    )
                    prop_id_by_rm: dict[int, int] = {
                        row.rightmove_id: row.id for row in existing_result
                    }

                new_items = [
                    (link, rm_id)
                    for link, rm_id in page_items
                    if rm_id not in prop_id_by_rm
                ]

                if new_items:
                    results = await asyncio.gather(
                        *(fetch_detail(link) for link, _ in new_items),
                        return_exceptions=True,
                    )
                else:
                    results = []

                async with SessionLocal() as session:
                    for (link, rm_id), detail in zip(new_items, results):
                        if isinstance(detail, Exception):
                            logger.warning(
                                f"Search {search_id}: listing {link} failed: {detail}"
                            )
                            total_failed += 1
                            continue
                        if detail is None:
                            total_failed += 1
                            continue
                        try:
                            async with session.begin_nested():
                                prop_id = await _upsert_property(session, detail)
                        except Exception as e:
                            logger.warning(
                                f"Search {search_id}: upsert {link} failed: {e}"
                            )
                            total_failed += 1
                            continue
                        if prop_id is not None:
                            prop_id_by_rm[rm_id] = prop_id

                    for _, rm_id in page_items:
                        prop_id = prop_id_by_rm.get(rm_id)
                        if prop_id is None:
                            continue
                        try:
                            async with session.begin_nested():
                                await session.execute(
                                    pg_insert(SearchProperty)
                                    .values(search_id=search_id, property_id=prop_id)
                                    .on_conflict_do_nothing()
                                )
                        except Exception as e:
                            logger.warning(
                                f"Search {search_id}: link prop {prop_id} failed: {e}"
                            )
                            continue
                        total_found += 1

                    await session.commit()

                results = None
                page_items = None
                new_items = None
                prop_id_by_rm = None
                gc.collect()

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
