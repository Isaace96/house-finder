import json
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from app.config import settings
from app.services.image_extractor import get_sqm_from_property_link

SQFT_TO_SQM = 0.092903

BASE_URL = "https://www.rightmove.co.uk"
PROPERTIES_PER_PAGE = 25
STARTING_INDEX = 0
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3

_headers = {"User-Agent": settings.rightmove_user_agent}


def _get_with_retries(url: str) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=_headers, timeout=30)
            if response.status_code in RETRY_STATUS_CODES:
                logger.warning(
                    f"{url} returned {response.status_code} (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2**attempt)
                    continue
            return response
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            logger.warning(
                f"{url} {type(e).__name__} (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(2**attempt)
    assert last_exc is not None
    raise last_exc


@dataclass
class PropertyDetails:
    link: str
    sqm: Optional[float]
    price: Optional[int]
    address: Optional[str]
    property_listing_type: str
    price_per_sqm: Optional[float] = None

    def __post_init__(self):
        if (self.sqm or 0) > 1 and (self.price or 0) > 1:
            self.price_per_sqm = self.price / self.sqm


def format_search_url(url: str, offset: int) -> str:
    index_text = "&index=0"
    index_text_with_offset = f"&index={STARTING_INDEX + offset}"
    if index_text in url:
        return url.replace(index_text, index_text_with_offset)
    return f"{url}{index_text_with_offset}"


def extract_property_links_from_page(page_content: bytes) -> list[str]:
    soup = BeautifulSoup(page_content, "html.parser")
    links = soup.find_all("a", class_="propertyCard-link")
    return [link.get("href") for link in links if link.get("href")]


def rightmove_id_from_link(link: str) -> Optional[int]:
    m = re.search(r"/properties/(\d+)", link)
    return int(m.group(1)) if m else None


def _get_area_from_info_reel(soup: BeautifulSoup) -> Optional[float]:
    for info_reel in soup.findAll("dl", attrs={"data-test": "infoReel"}):
        sqm_element = info_reel.find(
            string=lambda text: text and "sq m" in text
        )
        if sqm_element:
            try:
                return float(sqm_element.split()[0])
            except ValueError as e:
                logger.warning(f"sqm parse error: {e}")
    return None


def _get_price_from_soup(soup: BeautifulSoup) -> Optional[int]:
    prices = soup.find_all("span", string=lambda text: text and "£" in text)
    for price in prices:
        numeric_text = "".join(filter(str.isdigit, price.get_text()))
        try:
            return int(numeric_text)
        except ValueError:
            continue
    return None


def _get_address_from_soup(soup: BeautifulSoup) -> Optional[str]:
    address = soup.find(id="mapTitleScrollAnchor")
    return address.get_text() if address else None


def _extract_page_model(html_text: str) -> Optional[dict[str, Any]]:
    soup = BeautifulSoup(html_text, "html.parser")
    for script in soup.find_all("script"):
        txt = script.string
        if not txt or "window.PAGE_MODEL" not in txt:
            continue
        start = txt.index("window.PAGE_MODEL")
        eq = txt.index("=", start) + 1
        try:
            obj, _ = json.JSONDecoder().raw_decode(txt[eq:].lstrip())
            return obj
        except json.JSONDecodeError:
            return None
    return None


def _sqm_from_page_model(page_model: dict[str, Any]) -> Optional[float]:
    pd = page_model.get("propertyData") or {}
    sizings = pd.get("sizings") or []
    for s in sizings:
        if s.get("unit") == "sqm":
            val = s.get("minimumSize") or s.get("maximumSize")
            if val:
                return float(val)
    for s in sizings:
        if s.get("unit") == "sqft":
            val = s.get("minimumSize") or s.get("maximumSize")
            if val:
                return float(val) * SQFT_TO_SQM
    return None


def _price_from_page_model(page_model: dict[str, Any]) -> Optional[int]:
    pd = page_model.get("propertyData") or {}
    prices = pd.get("prices") or {}
    display = prices.get("primaryPrice") or ""
    digits = "".join(c for c in display if c.isdigit())
    return int(digits) if digits else None


def _address_from_page_model(page_model: dict[str, Any]) -> Optional[str]:
    pd = page_model.get("propertyData") or {}
    addr = pd.get("address") or {}
    return addr.get("displayAddress")


def fetch_property_links_for_page(query_url: str, offset: int) -> list[str]:
    url = format_search_url(query_url, offset)
    response = _get_with_retries(url)
    if response.status_code != 200:
        logger.info(f"Listing page failed. Status: {response.status_code}")
        return []
    return extract_property_links_from_page(response.content)


def extract_data_from_properties_link(
    property_link: str, search_type: str
) -> Optional[PropertyDetails]:
    res = _get_with_retries(f"{BASE_URL}{property_link}")
    if res.status_code != 200:
        logger.warning(f"Property page {property_link} status {res.status_code}")
        return None

    page_model = _extract_page_model(res.text)
    sqm: Optional[float] = None
    price: Optional[int] = None
    address: Optional[str] = None

    if page_model:
        sqm = _sqm_from_page_model(page_model)
        price = _price_from_page_model(page_model)
        address = _address_from_page_model(page_model)

    if sqm is None or price is None or address is None:
        soup = BeautifulSoup(res.content, "html.parser")
        if sqm is None:
            sqm = _get_area_from_info_reel(soup)
        if price is None:
            price = _get_price_from_soup(soup)
        if address is None:
            address = _get_address_from_soup(soup)

    if not sqm:
        try:
            sqm = get_sqm_from_property_link(property_link)
        except Exception as e:
            logger.warning(f"OCR fallback failed for {property_link}: {e}")
            sqm = None

    return PropertyDetails(
        link=property_link,
        sqm=sqm,
        price=price,
        address=address,
        property_listing_type=search_type,
    )
