import csv
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Any, List
import webbrowser
import yaml
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from typing import Optional
from bs4 import BeautifulSoup
import requests
from tinydb import TinyDB, Query

from image_extractor import get_sqm_from_property_link
from loguru import logger

logger.level("INFO")
logger.add("properties.log")

class PropertyListingTypes(str,Enum):
    RENTAL: str = "Rental"
    SALES: str = "Sale"

with open(Path(__file__).parent / 'config.yaml') as f:
    cfg = yaml.safe_load(f)

PROPERTIES_PER_PAGE = 25
STARTING_INDEX = 0
BASE_URL = 'https://www.rightmove.co.uk'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

QUERY_URL = cfg['query_url']
SEARCH_TYPE = PropertyListingTypes(cfg['search_type'])
MAX_PAGES = cfg['max_pages']
SQM_MIN_LIMIT = cfg['sqm_min']
SQM_MAX_LIMIT = cfg['sqm_max']
TOP_N_TABS = cfg['top_n_tabs']
open_webbrowser = cfg['open_webbrowser']

property_count = 0
db = TinyDB(cfg['db_path'])
CSV_FILE_NAME = f"data_{datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
query = Query()

db.update({'status': 'unreviewed'}, ~query.status.exists())



class PropertyDetails(BaseModel):
    link: str
    sqm: Optional[float]
    price: Optional[int]
    price_per_sqm: Optional[float] = None
    address: Optional[str] = None
    rightmove_properties: Optional[Any] = None
    included_in_query_results: list[str] = []
    property_listing_type: PropertyListingTypes
    status: str = "unreviewed"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if (self.sqm or 0) > 1 and (self.price or 0) > 1:
            self.price_per_sqm = self.price / self.sqm

    def add_source_query(self, query: str):
        if query in self.included_in_query_results:
            return
        else:
            self.included_in_query_results.append(query)
    


def format_search_url(url, offset):
    index_text = "&index=0"
    index_text_with_offset = f"&index={STARTING_INDEX + offset}"
    if index_text in url:
        return url.replace(index_text, index_text_with_offset)
    else:
        return f"{url}{index_text_with_offset}"

def extract_property_links_from_page(page_content: bytes) -> list[str]:
    properties_on_page_links = []
    soup = BeautifulSoup(page_content, 'html.parser')
    property_links = soup.find_all('a', class_='propertyCard-link')
    for link in property_links:
        href = link.get('href')
        properties_on_page_links.append(href)
    return properties_on_page_links



def extract_data_from_properties_link(property_link: str) -> PropertyDetails:
    def get_area_from_info_reel(soup: BeautifulSoup):
        all_info_reels = soup.findAll('dl', attrs={'data-test': 'infoReel'})
        for info_reel in all_info_reels:
            sqm_element = info_reel.find(string=lambda text: text and 'sq m' in text) #maybe look for more different texts
        
            if sqm_element:
                try:
                    return float(sqm_element.split()[0])
                except ValueError as e:
                    logger.warning(f"No sqm from {property_link} html floor plan element - value error - {e}")
        return None

    def get_price_from_soup(soup: BeautifulSoup):
        prices = soup.find_all('span', string=lambda text: text and '£' in text)
        for price in prices:
            numeric_text = ''.join(filter(str.isdigit, price.get_text()))
            try:
                return int(numeric_text)
            except ValueError as e:
                logger.warning(f"No price from {property_link} text found {numeric_text} - value error - {e}")
        return None

    def get_address_from_soup(soup: BeautifulSoup) -> Optional[str]:
        address = soup.find(id="mapTitleScrollAnchor")
        if address:
            return address.get_text()
        else:
            return None
        

    def get_raw_json_text_from_soup(soup: BeautifulSoup) -> Optional[str]:
        script_text_pattern = 'window.PAGE_MODEL = ' 
        script_elements = soup.find_all('script')
        for script_element in script_elements:
            script_text = script_element.string
            if script_text is not None and script_text_pattern in script_text:
                return script_text.replace(script_text_pattern, '').strip().replace('.propertyData.dfpAdInfo.targeting', '')
            
        return None

    def get_rightmove_properties_from_soup(soup: BeautifulSoup) -> Optional[str]:
        text = get_raw_json_text_from_soup(soup)
        if text:
            return json.loads(text)
        else:
            return None

    res = requests.get(f"{BASE_URL}{property_link}", headers=HEADERS)
    if res.status_code == 200:
        soup = BeautifulSoup(res.content, 'html.parser')
        sqm = get_area_from_info_reel(soup)
        price = get_price_from_soup(soup)
        address = get_address_from_soup(soup)
        #rightmove_properties = get_rightmove_properties_from_soup(soup)

        if not sqm:
            sqm = get_sqm_from_property_link(property_link)
        
        details = PropertyDetails(link=property_link, sqm=sqm, price=price, property_listing_type=SEARCH_TYPE, address=address, rightmove_properties=None)
        
        details.add_source_query(QUERY_URL)
        return details
    else:
        res.raise_for_status()


def find_properties_on_page(offset: int):
    global properties_found, property_count

   
    url = format_search_url(QUERY_URL, offset)
    response = requests.get(url, headers=HEADERS)
    properties_on_page_links = []

    if response.status_code == 200:
        properties_on_page_links = extract_property_links_from_page(response.content)
    else:
        logger.info("Failed to retrieve the webpage. Status code:", response.status_code)

    for property_link in properties_on_page_links:
        property_count += 1
        if db.get(query.link == property_link) is not None:
            logger.debug(f"{property_link} - Already in database")
            continue

        details = extract_data_from_properties_link(property_link)
        db.insert(dict(details))
                

for i in range(0, MAX_PAGES, 1):
    logger.info(f"Finding property on page {i} of {MAX_PAGES}")
    find_properties_on_page(i * PROPERTIES_PER_PAGE)

logger.info(f"Found {len(db.all())} property sqm found of  {property_count} properties")
properties_found: List[PropertyDetails] = []

logger.info(f"Finding Properties with sqm > {SQM_MIN_LIMIT} from database")
for doc in db.search((query.sqm != None) & (query.sqm > SQM_MIN_LIMIT) & (query.sqm < SQM_MAX_LIMIT) & (query.property_listing_type == SEARCH_TYPE) & (query.status != "rejected")):
    properties_found.append(PropertyDetails(**doc))

logger.info(f"{len(properties_found)} properties found of {len(db.all())} in database")

with open(CSV_FILE_NAME, 'w', newline='') as csvfile:
    logger.info(f"Writing to csv {CSV_FILE_NAME}")
    writer = csv.writer(csvfile)
    writer.writerow(['sqm','pounds per m sq', 'price', 'address','link'])
    for p in properties_found:
        logger.info(f"{p.sqm}: {p.link}")
        writer.writerow([f"{p.sqm}",f"{p.price_per_sqm}",f"{p.price}",f"{p.address}",f"{BASE_URL}{p.link}"])

if open_webbrowser:
    properties_found.sort(key=lambda x: x.price_per_sqm)
    tabs_to_open = properties_found[:TOP_N_TABS]
    logger.info(f"Opening web browser with {len(tabs_to_open)} tabs")
    for p in tabs_to_open:
        webbrowser.open(f"{BASE_URL}{p.link}")
    