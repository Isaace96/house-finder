from app.services.scraper import (
    extract_property_links_from_page,
    format_search_url,
    rightmove_id_from_link,
)


def test_format_search_url_replaces_index():
    url = "https://www.rightmove.co.uk/search?foo=bar&index=0"
    assert format_search_url(url, 50).endswith("&index=50")
    assert "&index=0" not in format_search_url(url, 50)


def test_format_search_url_appends_if_missing():
    url = "https://www.rightmove.co.uk/search?foo=bar"
    assert format_search_url(url, 25) == url + "&index=25"


def test_extract_property_links_from_page_parses_cards():
    html = b"""
    <html><body>
      <a class="propertyCard-link" href="/properties/111#/?channel=RES_BUY">A</a>
      <a class="propertyCard-link" href="/properties/222#/?channel=RES_BUY">B</a>
      <a class="other" href="/nope">X</a>
    </body></html>
    """
    assert extract_property_links_from_page(html) == [
        "/properties/111#/?channel=RES_BUY",
        "/properties/222#/?channel=RES_BUY",
    ]


def test_rightmove_id_from_link():
    assert rightmove_id_from_link("/properties/123456#/?channel=RES_BUY") == 123456
    assert rightmove_id_from_link("/properties/999/floorplan?x=1") == 999
    assert rightmove_id_from_link("/no-id-here") is None
