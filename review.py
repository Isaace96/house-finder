import json
import re
from pathlib import Path

import requests
import yaml
from bs4 import BeautifulSoup
from flask import Flask, abort, jsonify, redirect, render_template, url_for
from tinydb import Query, TinyDB

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"

BUCKETS = ("unreviewed", "shortlisted", "rejected")

with open(Path(__file__).parent / "config.yaml") as f:
    cfg = yaml.safe_load(f)

app = Flask(__name__)
db = TinyDB(cfg["db_path"])
q = Query()

db.update({"status": "unreviewed"}, ~q.status.exists())

SQM_MIN = cfg["sqm_min"]
SQM_MAX = cfg["sqm_max"]
SEARCH_TYPE = cfg["search_type"]


def rightmove_id(link: str) -> int | None:
    m = re.search(r"/properties/(\d+)", link)
    return int(m.group(1)) if m else None


def filtered(status: str) -> list[dict]:
    docs = db.search(
        (q.sqm != None)
        & (q.sqm > SQM_MIN)
        & (q.sqm < SQM_MAX)
        & (q.property_listing_type == SEARCH_TYPE)
        & (q.status == status)
    )
    for d in docs:
        d["rightmove_id"] = rightmove_id(d["link"])
        d["full_url"] = f"https://www.rightmove.co.uk{d['link']}"
    docs.sort(key=lambda d: d.get("price_per_sqm") or float("inf"))
    return docs


def counts() -> dict[str, int]:
    base = (
        (q.sqm != None)
        & (q.sqm > SQM_MIN)
        & (q.sqm < SQM_MAX)
        & (q.property_listing_type == SEARCH_TYPE)
    )
    return {b: db.count(base & (q.status == b)) for b in BUCKETS}


@app.route("/")
def root():
    return redirect(url_for("review", bucket="unreviewed"))


@app.route("/<bucket>")
def review(bucket: str):
    if bucket not in BUCKETS:
        abort(404)
    return render_template(
        "review.html",
        bucket=bucket,
        buckets=BUCKETS,
        properties=filtered(bucket),
        counts=counts(),
    )


@app.post("/set-status/<int:rm_id>/<new_status>")
def set_status(rm_id: int, new_status: str):
    if new_status not in BUCKETS:
        abort(400)
    db.update({"status": new_status}, q.link.matches(rf"/properties/{rm_id}(#|/|$)"))
    return ""


_preview_cache: dict[int, dict] = {}


def _extract_page_model(html_text: str) -> dict | None:
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


@app.get("/preview/<int:rm_id>")
def preview(rm_id: int):
    if rm_id in _preview_cache:
        return jsonify(_preview_cache[rm_id])

    doc = db.get(q.link.matches(rf"/properties/{rm_id}(#|/|$)"))
    if not doc:
        abort(404)

    url = f"https://www.rightmove.co.uk{doc['link']}"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        return jsonify({"error": f"Fetch failed: {e}"}), 502

    data = _extract_page_model(r.text)
    if not data:
        return jsonify({"error": "Could not parse PAGE_MODEL"}), 502

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

    payload = {
        "id": rm_id,
        "url": url,
        "address": address_obj.get("displayAddress") or doc.get("address") or "",
        "postcode": address_obj.get("outcode") or "",
        "price": price_obj.get("primaryPrice") or (f"£{doc['price']:,}" if doc.get("price") else ""),
        "bedrooms": pd.get("bedrooms"),
        "bathrooms": pd.get("bathrooms"),
        "property_type": pd.get("propertySubType") or analytics.get("propertyData", {}).get("propertyType"),
        "tenure": (pd.get("tenure") or {}).get("tenureType"),
        "sqm": doc.get("sqm"),
        "price_per_sqm": doc.get("price_per_sqm"),
        "description": (pd.get("text") or {}).get("description") or "",
        "features": pd.get("keyFeatures") or [],
        "images": images,
        "floorplans": floorplans,
        "stations": stations,
        "agent": (pd.get("customer") or {}).get("branchDisplayName"),
    }
    _preview_cache[rm_id] = payload
    return jsonify(payload)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
