import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from app.config import settings
from app.services.image_extractor import get_sqm_from_property_link

BASE_URL = "https://www.rightmove.co.uk"
PROPERTIES_PER_PAGE = 25
STARTING_INDEX = 0

_headers = {"User-Agent": settings.rightmove_user_agent}


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


def fetch_property_links_for_page(query_url: str, offset: int) -> list[str]:
    url = format_search_url(query_url, offset)
    response = requests.get(url, headers=_headers, timeout=30)
    if response.status_code != 200:
        logger.info(f"Listing page failed. Status: {response.status_code}")
        return []
    return extract_property_links_from_page(response.content)


def extract_data_from_properties_link(
    property_link: str, search_type: str
) -> Optional[PropertyDetails]:
    res = requests.get(f"{BASE_URL}{property_link}", headers=_headers, timeout=30)
    if res.status_code != 200:
        logger.warning(f"Property page {property_link} status {res.status_code}")
        return None

    soup = BeautifulSoup(res.content, "html.parser")
    sqm = _get_area_from_info_reel(soup)
    price = _get_price_from_soup(soup)
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
