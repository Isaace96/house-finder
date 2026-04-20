import math
import pytest
from image_extractor import SQF_PHRASES, SQM_PHRASES, get_area, get_sqm_from_property_link

@pytest.mark.parametrize("link, sqm", [
    ("/properties/143395439#/?channel=RES_BUY",63.45),
    ("/properties/144972980#/floorplan?activePlan=1&channel=RES_BUY", 55.7),
    ("/properties/141061556#/floorplan?activePlan=1&channel=RES_BUY",55.0),
    ("/properties/140924081#/?channel=RES_BUY", 94.68),
    #("/properties/86756916#/floorplan",77),
    #("/properties/143945681#/floorplan?activePlan=1&channel=RES_LET", 81.85),
    ("/properties/144948308#/floorplan?activePlan=1&channel=RES_LET",62.4),
    ("/properties/145033895#/floorplan?activePlan=1&channel=RES_BUY",63.29),
    ("/properties/144486662#/?channel=RES_BUY",85.55),
    ("/properties/145047158#/?channel=RES_BUY",71.2),
    ("/properties/144983894#/floorplan?activePlan=2&channel=RES_BUY", 65.0),
    ("/properties/144316760#/floorplan?activePlan=1&channel=RES_BUY", 99.3),
    ("/properties/145189997#/?channel=RES_LET", 83.8),
    ("/properties/145193189#/?channel=RES_LET", 74.97),
    ("/properties/144868022#/?channel=RES_BUY",67.91)
])
def test_get_sqm_from_image(link, sqm):
    assert math.isclose(get_sqm_from_property_link(link), sqm,abs_tol=0.1)

@pytest.mark.parametrize("text, sqm, phrases, is_sqft", [
    ('Hawthorn Court,\nWarwick Drive, SW15\n\nCc) - Ceiling Height\n\nKitchen\n99" x 9\'6"\n2.97 x 2.90m\n\nReception\nRoom\n19\'2" x 10\'8"\n5.84 x 3.25m\n\nPrincipal\nBedroom\n12\'5" x 96"\n\n| 3.78 x 2.90m\n\nBalcony\n\nBedroom\n11\'2"x9\'6"\n3.40 x 2.90m\n\nFourth Floor\nApprox Gross Internal Area 683 Sq Ft - 63.45 Sq M\n\nFor Illustration Purposes Only - Not To Scale\nwww.goldlens.co.uk\nRef No. 021377F\n\n',63.45, SQM_PHRASES, False),
    ('@ ludlowthompson Lagonda House, Tidworth Road, E3 55.7 sq m/599 sa ft\n\nReception Room Bedroom\n15\'10" x 12\'0" 9\'11" x 6\'9" Bedroom\n4.82m x 3.67m 3.02m x 2.05m 14\'9" x 8\'7"\n4.50m x 2.61m\n\nKitchen\n9\'7" x 8\'8"\n2.92m x 2.64m\n\nBathroom\n8\'11" x 4\'9"\n2.71m x 1.45m\nThird Floor\n| a,\n1155.7 sqm / 599 sqft 2sqm/23 sqft 0.6 sqm/6 sqft + 0.0sqm/0.0 sqft\nDisclaimer : Floorplan measurements are approximate and are for illustrative purposes only. While we do not doubt the floorplan accuracy Maison\nand completeness, you or your advisors should conduct a careful, independent investigation of the property in respect of monetary valuation VUE\n', 55.7, SQM_PHRASES, False),
    ("reundtree Windsor Court, NW11\n\nal estate\n\n02/02/2023 94,752,744\n\nDINING ROOM\n5.50m x 3.1m\n(181 x 10'2)\n\nMAIN BEDROOM\n5.49m x 3.33m\n(18°0 x 10'11)\n\nBEDROOM 2\n2.81m x 2.49m\n(9'3 x 82)\n\n— First Floor\n\n194.68 sqm /101913 eaft 89.85 sqm /96714 saft\n\n@spec\n\nVerified\n\n(0.00 sqm / 0.00 saft\n\n94.68 sqm / 1019.13 sqft\n\nRECEPTION\n4.87m x 3.46m\n(16'0 x 11'4)\n\nKITCHEN\n4.13m x 3.30m\n(13'7 x 10°10)\n\n0.00 sqm /0.00 saft\n", 1019.13, SQF_PHRASES, True),
    ('@ ludlowthompson Anderson Square, E3 99.3 sq m/ 1069 sq ft\n\nShower Room Bathroom\n7\'0" x 5\'3" 7\'0" x 7\'0"\n2.13m x 1.61m 2.13m x 2.13m\n\nBedroom\n20\'6" x 13\'1"\n6.26m x 4.00m\n\nBedroom I\n\n16\'4" x 9\'0"\n4.97m x 2.74m\n\nReception Room /\nKitchen\n277" x 12\'4"\n8.40m x 3.77m\n\nLower Ground Floor\n\n[199.3 sqm/ 1067 sqit\n\nOT\n113.6 sqm/39sqit 0.0 sqm/0.0 sqit £ 0.05qm/0.0 sat\n\nDisclaimer : Floorplan measurements are approximate and are for illustrative purposes only. While we do not doubt the floorplan accuracy Maison\nand completeness, you or your advisors should conduct a careful, independent investigation of the property in respect of monetary valuation VUE\n', 1069, SQF_PHRASES, True)
])
def test_get_sqm(text, sqm, phrases, is_sqft):
    assert math.isclose(get_area(text, phrases, is_sqft) , sqm)
