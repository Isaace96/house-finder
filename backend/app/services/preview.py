import json
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from app.config import settings

BASE_URL = "https://www.rightmove.co.uk"
_headers = {"User-Agent": settings.rightmove_user_agent}


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


def fetch_preview(rightmove_id: int, link: str, cached_sqm: Optional[float] = None,
                  cached_price: Optional[int] = None, cached_price_per_sqm: Optional[float] = None,
                  cached_address: Optional[str] = None) -> dict[str, Any]:
    url = f"{BASE_URL}{link}"
    r = requests.get(url, headers=_headers, timeout=20)
    r.raise_for_status()

    data = _extract_page_model(r.text)
    if not data:
        raise ValueError("Could not parse PAGE_MODEL")

    pd = data.get("propertyData") or {}
    analytics = data.get("analyticsInfo") or {}

    images = []
    for img in pd.get("images") or []:
        src = img.get("masterUrl") or img.get("srcUrl") or img.get("url")
        if src:
            images.append({"url": src, "caption": img.get("caption") or ""})

    floorplans = [fp.get("url") for fp in (pd.get("floorplans") or []) if fp.get("url")]

    stations = []
    for s in pd.get("nearestStations") or []:
        stations.append({
            "name": s.get("name"),
            "distance": s.get("distance"),
            "unit": s.get("unit"),
            "types": s.get("types") or [],
        })

    price_obj = pd.get("prices") or {}
    address_obj = pd.get("address") or {}

    return {
        "id": rightmove_id,
        "url": url,
        "address": address_obj.get("displayAddress") or cached_address or "",
        "postcode": address_obj.get("outcode") or "",
        "price": price_obj.get("primaryPrice")
        or (f"£{cached_price:,}" if cached_price else ""),
        "bedrooms": pd.get("bedrooms"),
        "bathrooms": pd.get("bathrooms"),
        "property_type": pd.get("propertySubType")
        or analytics.get("propertyData", {}).get("propertyType"),
        "tenure": (pd.get("tenure") or {}).get("tenureType"),
        "sqm": cached_sqm,
        "price_per_sqm": cached_price_per_sqm,
        "description": (pd.get("text") or {}).get("description") or "",
        "features": pd.get("keyFeatures") or [],
        "images": images,
        "floorplans": floorplans,
        "stations": stations,
        "agent": (pd.get("customer") or {}).get("branchDisplayName"),
    }
