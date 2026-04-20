from io import BytesIO
import re
from typing import Optional
from PIL import Image
from bs4 import BeautifulSoup
from loguru import logger
import pytesseract
import requests

SQM_PHRASES = ["sq\.", "sqm", "SQM","SqM", "Sq", "Sq M","SQ\.M\.","SQ\. M\.","SQ\.M,", "Sq M", "sq m","m2"]
SQF_PHRASES = ["sqft", "sq ft","ft","SqFt"]
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
MAX_SQM_LIMIT = 200
MAX_SQF_LIMIT = 2000

MIN_SQM_LIMIT = 10
SQFT_IN_SQM = 10.764

def extract_area(sqm_text: str, text: str, limit = MAX_SQM_LIMIT):
    pattern = r'(\d+\.\d+)\s' + sqm_text
    pattern_whole_area = r'(\d+)\s' + sqm_text

    matches = re.findall(pattern, text)
    if not matches:
        matches = re.findall(pattern_whole_area, text)
    if matches:
        try:
            area_matches = [float(m) for m in matches if float(m) < limit]
            area = 0
            if len(area_matches) != 0:
                area =  max(area_matches)
            else:
                area = max([float(m) / SQFT_IN_SQM for m in area_matches])
            
            if area < MIN_SQM_LIMIT:
                return None
            else:
                return area
            
        except ValueError:
            return None
    else: 
        return None

def get_area(text: str, phrases: list[str], is_sqft= False):
    for phrase in phrases:
        if is_sqft:
            area = extract_area(phrase, text, MAX_SQF_LIMIT)
        else:
            area = extract_area(phrase, text)
        if area is not None:
            return area
    return None

def get_sqm_from_image(image: Image):
    text = pytesseract.image_to_string(image, config='--psm 3')
    sqm = get_area(text, SQM_PHRASES)
    if sqm is None:
        text = pytesseract.image_to_string(image, config='--psm 6')
        sqm = get_area(text, SQM_PHRASES)
    
    sqf = get_area(text, SQF_PHRASES, True)
    
    if sqf is None:
        return sqm
    elif sqf is None and sqm is None:
        return None
    
    sqm_from_sqf = round(sqf / SQFT_IN_SQM, 2)
    if sqm is None:
        return sqm_from_sqf
    elif sqm_from_sqf > sqm:
        return sqm
    else:
        return sqm_from_sqf

def find_floor_plans(soup: BeautifulSoup):
    alternative_texts = [r'fp', r'floor plan', r'floorplan']
    floor_plans = []
    for alt_text in alternative_texts:
        item = soup.findAll('img', alt=re.compile(alt_text, re.IGNORECASE))
        floor_plans.extend(item)
    
    src_link_texts = [r'FLP', r'Floorplan',r'FloorPlan']
    for text in src_link_texts:
            item = soup.findAll('img', src=re.compile(text, re.IGNORECASE))
            floor_plans.extend(item)
    return floor_plans

def find_image_srcs(url: str) -> Optional[str]:
    response = requests.get(url, headers=headers)
    links = []

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        floorplan_imgs = find_floor_plans(soup)
        for floorplan_img in floorplan_imgs:
            if floorplan_img:
                src = floorplan_img.get('src')
                logger.debug("Found the 'img' element with alt='Floorplan' and src='{}'".format(src))
                links.append(src)
            else:
                logger.info("The 'img' element with alt attribute 'Floorplan' not found.")
    else:
        logger.info("Failed to retrieve the webpage. Status code:", response.status_code)
    return list(dict.fromkeys(links))

def load_image(image_url) -> Image:
    
    response = requests.get(image_url, headers=headers)
    if response.status_code == 200:
        image_bytes = BytesIO(response.content)
        img = Image.open(image_bytes)
        return img
    else:
        logger.info("Failed to retrieve the image. Status code:", response.status_code)

def format_property_link_to_floorplan(link):
    parts = link.split("/")
    id =  [x for x in parts if "#" in x][0]
    return f"https://www.rightmove.co.uk/properties/{id}/floorplan?activePlan=1&channel=RES_BUY"

url = "https://www.rightmove.co.uk/properties/144868022#/?channel=RES_BUY"

def ensure_max_size_image(image_url: str):
    return re.sub(r'_max_\d+x\d+', '', image_url)

def get_sqm_from_property_link(url):
    url = format_property_link_to_floorplan(url)
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


