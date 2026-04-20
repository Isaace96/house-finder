import re
from io import BytesIO
from typing import Optional

import pytesseract
import requests
from bs4 import BeautifulSoup
from loguru import logger
from PIL import Image

from app.config import settings

SQM_PHRASES = [
    "sq\\.",
    "sqm",
    "SQM",
    "SqM",
    "Sq",
    "Sq M",
    "SQ\\.M\\.",
    "SQ\\. M\\.",
    "SQ\\.M,",
    "Sq M",
    "sq m",
    "m2",
]
SQF_PHRASES = ["sqft", "sq ft", "ft", "SqFt"]
MAX_SQM_LIMIT = 200
MAX_SQF_LIMIT = 2000
MIN_SQM_LIMIT = 10
SQFT_IN_SQM = 10.764

_headers = {"User-Agent": settings.rightmove_user_agent}


def extract_area(sqm_text: str, text: str, limit: float = MAX_SQM_LIMIT):
    pattern = r"(\d+\.\d+)\s" + sqm_text
    pattern_whole_area = r"(\d+)\s" + sqm_text

    matches = re.findall(pattern, text)
    if not matches:
        matches = re.findall(pattern_whole_area, text)
    if matches:
        try:
            area_matches = [float(m) for m in matches if float(m) < limit]
            area = 0
            if len(area_matches) != 0:
                area = max(area_matches)
            else:
                area = max([float(m) / SQFT_IN_SQM for m in area_matches])

            if area < MIN_SQM_LIMIT:
                return None
            return area
        except ValueError:
            return None
    return None


def get_area(text: str, phrases: list[str], is_sqft: bool = False):
    for phrase in phrases:
        if is_sqft:
            area = extract_area(phrase, text, MAX_SQF_LIMIT)
        else:
            area = extract_area(phrase, text)
        if area is not None:
            return area
    return None


def get_sqm_from_image(image: Image.Image):
    text = pytesseract.image_to_string(image, config="--psm 3")
    sqm = get_area(text, SQM_PHRASES)
    if sqm is None:
        text = pytesseract.image_to_string(image, config="--psm 6")
        sqm = get_area(text, SQM_PHRASES)

    sqf = get_area(text, SQF_PHRASES, True)

    if sqf is None:
        return sqm
    if sqf is None and sqm is None:
        return None

    sqm_from_sqf = round(sqf / SQFT_IN_SQM, 2)
    if sqm is None:
        return sqm_from_sqf
    if sqm_from_sqf > sqm:
        return sqm
    return sqm_from_sqf


def find_floor_plans(soup: BeautifulSoup):
    alternative_texts = [r"fp", r"floor plan", r"floorplan"]
    floor_plans = []
    for alt_text in alternative_texts:
        item = soup.findAll("img", alt=re.compile(alt_text, re.IGNORECASE))
        floor_plans.extend(item)

    src_link_texts = [r"FLP", r"Floorplan", r"FloorPlan"]
    for text in src_link_texts:
        item = soup.findAll("img", src=re.compile(text, re.IGNORECASE))
        floor_plans.extend(item)
    return floor_plans


def find_image_srcs(url: str) -> list[str]:
    response = requests.get(url, headers=_headers, timeout=30)
    links: list[str] = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        floorplan_imgs = find_floor_plans(soup)
        for floorplan_img in floorplan_imgs:
            src = floorplan_img.get("src")
            if src:
                logger.debug(f"Found floorplan img src={src}")
                links.append(src)
    else:
        logger.info(f"Failed to retrieve floorplan page. Status: {response.status_code}")
    return list(dict.fromkeys(links))


def load_image(image_url: str) -> Optional[Image.Image]:
    response = requests.get(image_url, headers=_headers, timeout=30)
    if response.status_code == 200:
        return Image.open(BytesIO(response.content))
    logger.info(f"Failed to retrieve image. Status: {response.status_code}")
    return None


def format_property_link_to_floorplan(link: str) -> str:
    parts = link.split("/")
    ids = [x for x in parts if "#" in x]
    if ids:
        return f"https://www.rightmove.co.uk/properties/{ids[0]}/floorplan?activePlan=1&channel=RES_BUY"
    m = re.search(r"/properties/(\d+)", link)
    if m:
        return f"https://www.rightmove.co.uk/properties/{m.group(1)}#/floorplan?activePlan=1&channel=RES_BUY"
    return link


def ensure_max_size_image(image_url: str) -> str:
    return re.sub(r"_max_\d+x\d+", "", image_url)


def get_sqm_from_property_link(link: str) -> Optional[float]:
    url = format_property_link_to_floorplan(link)
    image_srcs = find_image_srcs(url)
    for image_src in image_srcs:
        image_src = ensure_max_size_image(image_src)
        image = load_image(image_src)
        if image is None:
            return None
        sqm = get_sqm_from_image(image)
        if sqm is not None:
            return sqm
    return None
