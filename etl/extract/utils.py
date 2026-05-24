"""
etl/extract/utils.py
--------------------
Shared helper utilities for all FBRef / StatsBomb extract scripts.
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata

import cloudscraper
import pandas as pd
import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DataFrame helpers
# ---------------------------------------------------------------------------

def flatten_soccerdata(df: pd.DataFrame) -> pd.DataFrame:
    """Reset MultiIndex and flatten hierarchical column names from soccerdata output."""
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            "_".join(str(c).strip() for c in col if str(c).strip()).lower()
            for col in df.columns
        ]
    else:
        df.columns = [str(c).lower().strip() for c in df.columns]
    df.columns = [re.sub(r"\s+", "_", c) for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """Lowercase, strip accents, normalize whitespace for fuzzy name matching."""
    if not isinstance(name, str):
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_str).strip().lower()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def get_session() -> cloudscraper.CloudScraper:
    """Cloudscraper session — bypasses Cloudflare JS challenge that FBRef uses."""
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    scraper.headers.update({"Accept-Language": "en-US,en;q=0.9"})
    return scraper


def rate_limited_get(
    session: cloudscraper.CloudScraper, url: str, pause: float = 4.0
) -> requests.Response:
    """GET request with polite rate limiting to avoid FBRef blocks."""
    time.sleep(pause)
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    # Force UTF-8 so ñ/á/é/etc. decode correctly regardless of server hint
    resp.encoding = "utf-8"
    return resp
