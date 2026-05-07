#!/usr/bin/env python3
"""Seed monitored_items table from vault preference files.

Run after deploying the deal-monitoring-news-curation branch:
  docker exec bede-data python /scripts/seed-monitored-items.py

Or from the host via the API (if accessible):
  BEDE_DATA_URL=http://localhost:8001 python scripts/seed-monitored-items.py
"""

import json
import os
import sys
import urllib.request
import urllib.error

BASE_URL = os.environ.get("BEDE_DATA_URL", "http://localhost:8001")

ITEMS = [
    {
        "category": "deal",
        "name": "Camping Gear",
        "config": json.dumps({
            "items": [
                {"name": "Mont Helium 300 (-1C)", "target_price": 450, "urls": [
                    "https://www.mont.com.au/products/helium-300-lightweight-down-sleeping-bag",
                    "https://www.paddypallin.com.au/mont-helium-300-sleeping-bag-w22.html",
                ]},
                {"name": "Mont Helium 450 (-7C)", "target_price": 550, "urls": [
                    "https://www.mont.com.au/products/helium-450-lightweight-down-sleeping-bag",
                ]},
                {"name": "Sea to Summit Spark -9C", "target_price": 500, "urls": [
                    "https://www.paddypallin.com.au/sea-to-summit-spark-down-sleeping-bag-9c.html",
                    "https://seatosummit.com.au/products/spark-down-sleeping-bag?variant=43615199985850",
                ]},
                {"name": "Sea to Summit Spark SpIII -8C", "target_price": 400, "urls": [
                    "https://www.paddypallin.com.au/sea-to-summit-spark-spiii-sleeping-bag-8-c.html",
                ]},
                {"name": "Macpac Dragonfly 400 (-5C)", "target_price": 420, "urls": [
                    "https://www.macpac.com.au/dragonfly-sleeping-bags",
                ]},
                {"name": "One Planet Nitrous series", "target_price": 450, "urls": [
                    "https://oneplanet.au/category/sleeping-bags/down/",
                ]},
                {"name": "Exped Ultra 5R (R4.8)", "target_price": 220, "urls": [
                    "https://www.tomsoutdoors.com.au/products/exped-ultra-5r-ultralight-4-season-sleeping-mat",
                    "https://ultralightgear.com.au/products/exped-ultra-5r-ultralight-4-season-sleeping-mat",
                    "https://www.mont.com.au/products/exped-ultra-5r",
                ]},
                {"name": "Nemo Tensor All-Season (R5.4)", "target_price": 250, "urls": [
                    "https://www.paddypallin.com.au/nemo-equipment-tensor-allseason-insulated-sleeping-mat.html",
                    "https://adventurecurated.com.au/products/nemo-tensor-all-season-ultralight-insulated-sleeping-pad",
                ]},
                {"name": "Nemo Tensor Extreme Conditions (R8.5)", "target_price": 300, "urls": [
                    "https://www.paddypallin.com.au/nemo-equipment-tensor-extreme-conditions-insulated-sleeping-mat.html",
                ]},
                {"name": "Sea to Summit Ether Light XR Insulated (R4.0)", "target_price": 220, "urls": [
                    "https://seatosummit.com.au/products/ether-light-xr-insulated-air-sleeping-pad",
                ]},
                {"name": "Sea to Summit Ether Light XR Pro (R7.4)", "target_price": 300, "urls": [
                    "https://seatosummit.com.au/products/ether-light-xr-pro-insulated-air-sleeping-pad",
                ]},
            ],
            "retailers": [
                {"name": "Paddy Pallin", "url": "https://www.paddypallin.com.au", "clearance_url": "https://www.paddypallin.com.au/clearance/equipment/sleeping-equipment.html"},
                {"name": "Mont", "url": "https://www.mont.com.au", "clearance_url": "https://www.mont.com.au/collections/sleeping-bag-clearance"},
                {"name": "Macpac", "url": "https://www.macpac.com.au"},
                {"name": "Sea to Summit AU", "url": "https://seatosummit.com.au"},
                {"name": "Tom's Outdoors", "url": "https://www.tomsoutdoors.com.au"},
                {"name": "Ultralight Gear", "url": "https://ultralightgear.com.au"},
                {"name": "Adventure Curated", "url": "https://adventurecurated.com.au"},
                {"name": "Snowys", "url": "https://www.snowys.com.au"},
                {"name": "Wild Earth", "url": "https://www.wildearth.com.au"},
                {"name": "Bogong Equipment", "url": "https://www.bogong.com.au"},
                {"name": "One Planet", "url": "https://oneplanet.au"},
            ],
            "thresholds": {
                "report_below_target": True,
                "notes": "Best sale window: end-of-winter clearance (Aug-Sep). During sale windows, alert even if price is above target."
            },
            "search_hints": [
                "OzBargain: search 'sleeping bag', 'sleeping mat', 'camping' in last 7 days",
                "Check retailer clearance pages directly",
                "Shopify stores (Mont, Sea to Summit) share common HTML structure",
            ],
            "stock_quirks": {
                "Paddy Pallin": "Out of Stock",
                "Wild Earth": "Sold Out / Notify Me",
                "Macpac": "greyed-out size picker",
                "Mont": "Notify Me form",
            },
        }),
    },
    {
        "category": "deal",
        "name": "Clothing",
        "config": json.dumps({
            "items": [
                {"name": "Shirts (M, L)", "sizes": ["M", "L"], "notes": "Button-up, casual and smart-casual"},
                {"name": "T-shirts (M, L)", "sizes": ["M", "L"], "notes": "Quality basics and graphic tees"},
                {"name": "Blundstone Men's Original", "sizes": ["US 9", "US 9.5", "US 10"], "notes": "Classic style, NOT work/safety"},
                {"name": "Blundstone Men's Classic", "sizes": ["US 9", "US 9.5", "US 10"]},
                {"name": "Blundstone Men's Dress", "sizes": ["US 9", "US 9.5", "US 10"]},
                {"name": "Blundstone Men's Heritage", "sizes": ["US 9", "US 9.5", "US 10"], "notes": "NOT work/safety models"},
                {"name": "Budgy Smuggler", "sizes": ["32"], "target_price": 40, "notes": "Men's swimming briefs only"},
                {"name": "Blundstone Kids", "notes": "For Joe Jr"},
            ],
            "retailers": [
                {"name": "RB Sellars", "url": "https://www.rbsellars.com.au", "sale_url": "https://www.rbsellars.com.au/collections/online-outlet"},
                {"name": "Proper Cloth", "url": "https://propercloth.com"},
                {"name": "AS Colour", "url": "https://www.ascolour.com.au", "sale_url": "https://www.ascolour.com.au/outlet/"},
                {"name": "Pendleton", "url": "https://pendletonwoolenmills.com.au"},
                {"name": "Budgy Smuggler", "url": "https://budgysmuggler.com.au", "sale_url": "https://budgysmuggler.com.au/collections/mens-outlet"},
                {"name": "Blundstone Official", "url": "https://www.blundstone.com.au"},
            ],
            "thresholds": {
                "report_any_discount": True,
                "notes": "Any percentage off is worth reporting. Blundstones: especially winter season (May-Aug)."
            },
            "search_hints": [
                "For brands with sale URLs, fetch the page directly",
                "For others, search '[Brand] sale shirts Australia'",
                "Patagonia AU currently unavailable - check periodically",
            ],
        }),
    },
    {
        "category": "deal",
        "name": "Vacuum",
        "config": json.dumps({
            "items": [
                {"name": "SEBO X7 Boost", "target_price": 1000, "rrp": 1100, "role": "Deep clean (weekly)", "notes": "Sensitive Choice + British Allergy Foundation approved. S-Class sealed filtration."},
                {"name": "Dreame L50 Ultra", "target_price": 900, "rrp": 999, "role": "Daily auto (robot)", "notes": "TUV Rheinland Allergy Care certified. HEPA 0.3um, 19500Pa, sealed 3.2L bag."},
            ],
            "alternatives": [
                {"name": "Dyson Gen5detect Absolute", "price": 1549, "notes": "Best cordless for allergies. Only if going single-vacuum route. Strong deal at $750."},
                {"name": "Dreame Z30 Station", "price": 999, "notes": "Best value cordless. HEPA H14, 310 AW."},
                {"name": "Miele Complete C3 Cat & Dog", "price_range": "699-879", "notes": "Alternative to SEBO."},
            ],
            "retailers": [
                {"name": "JB Hi-Fi", "url": "https://www.jbhifi.com.au"},
                {"name": "Harvey Norman", "url": "https://www.harveynorman.com.au"},
                {"name": "The Good Guys", "url": "https://www.thegoodguys.com.au"},
                {"name": "Bing Lee", "url": "https://www.binglee.com.au"},
                {"name": "Amazon AU", "url": "https://www.amazon.com.au"},
                {"name": "Appliances Online", "url": "https://www.appliancesonline.com.au"},
                {"name": "SEBO AU", "url": "https://sebo.com.au"},
                {"name": "SEBO AU Shop", "url": "https://shop.sebo.com.au"},
                {"name": "Dreame AU", "url": "https://dreame.com.au"},
                {"name": "Bunnings", "url": "https://www.bunnings.com.au"},
            ],
            "thresholds": {
                "budget": 2000,
                "notes": "Total budget A$2,000 for both. SEBO strong deal at $900. Dreame strong deal at $800. 20%+ off RRP = strong deal. Exclude eBay and refurbished."
            },
            "requirements": [
                "True HEPA (not HEPA-style/grade)",
                "No trigger hold - push-button or toggle",
                "Handles cat hair on hard floors, carpet, upholstery",
                "Bagged or sealed auto-empty preferred",
            ],
            "search_hints": [
                "StaticICE: search 'SEBO X7 Boost', 'Dreame L50 Ultra'",
                "OzBargain tags: vacuum-cleaner, robot-vacuum",
                "Dreame AU runs launch/flash sales",
                "SEBO pricing more stable - check Bunnings and specialist shops",
            ],
        }),
    },
    {
        "category": "deal",
        "name": "Grocery Staples",
        "config": json.dumps({
            "items": [
                {"name": "Jalna Greek Style Yoghurt Natural 2kg"},
                {"name": "Weet-Bix Cereal 1.2kg"},
                {"name": "Finish Dishwash Powder Lemon Sparkle 2kg"},
                {"name": "Huggies Size 4 nappies or pullups", "notes": "boys"},
                {"name": "Quilton 3 ply toilet paper 24 pack"},
                {"name": "OMO Ultimate powder 5kg"},
                {"name": "Hill's Science Diet Oral Care adult cat food 4kg"},
                {"name": "Apple Gift Cards", "notes": "any denomination"},
                {"name": "Carman's Muesli Bars 12 pack", "notes": "any variety"},
                {"name": "Sirena Tuna in Olive Oil", "notes": "95g tins or multipacks"},
                {"name": "San Remo Pasta 500g", "notes": "any shape"},
            ],
            "retailers": [
                {"name": "Coles", "url": "https://www.coles.com.au"},
                {"name": "Woolworths", "url": "https://www.woolworths.com.au"},
                {"name": "Aldi", "url": "https://www.aldi.com.au/en/special-buys/"},
                {"name": "Chemist Warehouse", "url": "https://www.chemistwarehouse.com.au"},
                {"name": "PetBarn", "url": "https://www.petbarn.com.au"},
                {"name": "PetStock", "url": "https://www.petstock.com.au"},
            ],
            "thresholds": {
                "report_any_discount": True,
                "notes": "Any discount vs regular shelf price. Half-price specials always notable. Bulk/multipack deals worth flagging."
            },
            "search_hints": [
                "OzBargain for each item by keyword",
                "Coles and Woolworths weekly specials (Wed-Tue)",
                "Aldi Special Buys rotate Wed and Sat",
            ],
        }),
    },
    {
        "category": "event",
        "name": "Events",
        "config": json.dumps({
            "artists": [
                {"name": "Four Tet", "genre": "electronic"},
                {"name": "Radiohead", "genre": "rock"},
                {"name": "The Gaslight Anthem", "genre": "rock"},
                {"name": "Sydney Symphony Orchestra", "genre": "classical"},
            ],
            "venues": [
                {"name": "Sydney Opera House", "url": "https://www.sydneyoperahouse.com"},
                {"name": "City Recital Hall", "url": "https://www.cityrecitalhall.com"},
                {"name": "Ticketek", "url": "https://www.ticketek.com.au"},
                {"name": "Ticketmaster", "url": "https://www.ticketmaster.com.au"},
                {"name": "Moshtix", "url": "https://www.moshtix.com.au"},
            ],
            "thresholds": {
                "max_results": 5,
                "lookahead_months": 3,
                "notes": "Quality over quantity. 3-5 strong matches per category. Check Google Calendar for conflicts."
            },
            "search_hints": [
                "Search each venue URL for artist/venue names",
                "Every event MUST link to a real webpage",
                "Rumours fine but must cite source URL",
            ],
        }),
    },
    {
        "category": "news",
        "name": "News Sources",
        "config": json.dumps({
            "sources": [
                {"name": "The Mandarin", "url": "https://www.themandarin.com.au", "topic": "public_sector"},
                {"name": "Government News", "url": "https://www.govnews.com.au", "topic": "public_sector"},
                {"name": "Digital.NSW", "url": "https://www.digital.nsw.gov.au/blog", "topic": "public_sector"},
                {"name": "Microsoft 365 Blog", "url": "https://techcommunity.microsoft.com/blog/microsoft365blog", "topic": "platform_tech"},
                {"name": "Power Platform Blog", "url": "https://www.microsoft.com/en-us/power-platform/blog", "topic": "platform_tech"},
                {"name": "Salesforce Admins Blog", "url": "https://admin.salesforce.com/blog", "topic": "platform_tech"},
                {"name": "Drupal Security Advisories", "url": "https://www.drupal.org/security", "topic": "platform_tech"},
                {"name": "TLDR AI", "url": "https://tldr.tech/ai", "topic": "ai"},
            ],
            "preferences": {
                "signal_over_firehose": True,
                "max_articles_per_source": 5,
            },
        }),
    },
]


def post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"  ERROR {e.code}: {error_body}", file=sys.stderr)
        return {"error": e.code}


def main():
    print(f"Seeding monitored_items at {BASE_URL}")
    for item in ITEMS:
        print(f"  {item['category']}/{item['name']}...", end=" ")
        result = post("/api/config/monitored-items", item)
        if "error" in result:
            print("FAILED")
        else:
            print(f"OK (id={result.get('id')})")

    print("\nDone. Verify with: GET /api/config/monitored-items")


if __name__ == "__main__":
    main()
