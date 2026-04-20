# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- Install deps: `poetry install`
- Run scraper: `poetry run python main.py`
- Run review app: `poetry run python review.py` → `http://localhost:5000`
- Run all tests: `poetry run pytest`
- Run the offline text-parsing test only: `poetry run pytest test_image_extractor.py::test_get_sqm`
- Run a single parametrized case: `poetry run pytest -k "<substring>"`

Note: `test_get_sqm_from_image` hits live Rightmove URLs and downloads floorplan images — it is slow and will break when listings are removed. `test_get_sqm` is pure-text and offline.

## Architecture

Two source files: `main.py` (orchestration + HTML scraping) and `image_extractor.py` (floorplan OCR fallback).

**Runtime shape — important:** `main.py` has no `if __name__ == "__main__"` guard and no entrypoint function. Importing or running the module executes the full pipeline: paginated HTTP scrape of Rightmove → TinyDB insert → CSV write → up to 10 `webbrowser.open` calls. Do not import `main` from tests or other scripts.

**Two-stage sqm extraction** (the core design):
1. `extract_data_from_properties_link` in `main.py` fetches the listing page and tries `get_area_from_info_reel`, which parses `<dl data-test="infoReel">` for an "sq m" string.
2. If that returns `None`, it falls back to `get_sqm_from_property_link` in `image_extractor.py`, which loads the `/floorplan` page, finds floorplan `<img>` elements (by `alt=/fp|floorplan/i` or `src=/FLP|Floorplan/i`), downloads each image, and runs Tesseract OCR. Both sqm and sqft patterns are matched; when both are present the smaller value wins (see `get_sqm_from_image`).

**TinyDB as persistent cache**: the DB path (set via `db_path` in `config.yaml`) is keyed by property `link`. Already-seen links are skipped on subsequent runs — change `db_path` or delete the file to force a re-scrape.

**Configuration — `config.yaml`**: all user-tunable knobs live here and are loaded at the top of `main.py` via `yaml.safe_load`:
- `query_url` — the Rightmove search URL (has `&index=0`; the code rewrites the index for pagination)
- `search_type` — `Sale` or `Rental` (string; parsed into `PropertyListingTypes`)
- `max_pages`, `sqm_min`, `sqm_max` — scrape depth and the post-scrape floor-area filter
- `db_path`, `open_webbrowser`, `top_n_tabs` — output and browser-tab behavior

Platform constants (BASE_URL, User-Agent, `PROPERTIES_PER_PAGE=25`, `STARTING_INDEX=0`) stay hardcoded in `main.py`.

**Review app** (`review.py`): a small Flask + HTMX + Tailwind (CDN) triage UI. Reads the same TinyDB and config as `main.py`. Each DB doc carries a `status` field (`unreviewed` / `shortlisted` / `rejected`) — `review.py` and `main.py` both run a one-shot backfill on startup for older docs missing the field. `main.py`'s final filter excludes `status == "rejected"` so rejected listings no longer appear in the top-N browser-tab open. Keyboard shortcuts in the UI: `j`/`k` nav, `o` open, `r` reject, `s` shortlist, `u` undo.

## External dependencies

`pytesseract` requires a local Tesseract OCR binary installed on the system (not a pure pip install). Without it the floorplan fallback will fail at runtime.

`.gitignore` excludes `*.csv` and `*.json`, so scraper outputs and TinyDB cache files are intentionally untracked.
