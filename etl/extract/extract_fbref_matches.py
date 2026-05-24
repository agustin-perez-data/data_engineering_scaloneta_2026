"""
etl/extract/extract_fbref_matches.py
--------------------------------------
Argentina national team match history — multi-source extract.

Sources (in priority order):
  1. StatsBomb open data  — WC 2022 + Copa América 2024 (with xG where available)
  2. OpenFootball TXT     — Copa América 2021
  3. Wikipedia tables     — CONMEBOL WCQ 2022 cycle + WCQ 2026 cycle

Output: data/raw/argentina_matches.csv
"""

from __future__ import annotations

import logging
import re
import sys
import time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_FILE = OUT_DIR / "argentina_matches.csv"

CUTOFF_DATE = "2021-06-01"

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def build_match_id(date_str: str, opponent: str) -> str:
    date_part = str(date_str).replace("-", "")
    opp_part = re.sub(r"\s+", "_", str(opponent).strip())[:10]
    return f"ARG_{date_part}_{opp_part}"


def _result(gf: int, ga: int) -> str:
    return "W" if gf > ga else ("D" if gf == ga else "L")


# ---------------------------------------------------------------------------
# Source 1: StatsBomb open data
# ---------------------------------------------------------------------------

def _from_statsbomb() -> pd.DataFrame:
    try:
        from statsbombpy import sb
    except ImportError:
        logger.warning("statsbombpy not installed — skipping StatsBomb source")
        return pd.DataFrame()

    # WC 2022 (comp_id=43, season_id=106) + Copa América 2024 (comp_id=223, season_id=282)
    TARGETS = [
        (43,  106, "FIFA World Cup"),
        (223, 282, "Copa América 2024"),
    ]

    rows: list[dict] = []
    for comp_id, season_id, comp_label in TARGETS:
        try:
            matches = sb.matches(competition_id=comp_id, season_id=season_id)
        except Exception as exc:
            logger.warning("StatsBomb %s: %s", comp_label, exc)
            continue

        arg = matches[
            matches["home_team"].astype(str).str.contains("Argentina", na=False)
            | matches["away_team"].astype(str).str.contains("Argentina", na=False)
        ].copy()

        logger.info("StatsBomb %s: %d Argentina matches", comp_label, len(arg))

        for _, m in arg.iterrows():
            home = str(m.get("home_team", ""))
            away = str(m.get("away_team", ""))
            is_home = "Argentina" in home
            opp = away if is_home else home
            gf = int(m.get("home_score" if is_home else "away_score") or 0)
            ga = int(m.get("away_score" if is_home else "home_score") or 0)
            date = str(m.get("match_date", ""))[:10]

            stage_raw = m.get("competition_stage", {})
            stage = stage_raw.get("name", "") if isinstance(stage_raw, dict) else str(stage_raw or "")

            rows.append({
                "date": date,
                "competition": comp_label,
                "stage": stage,
                "venue": "Home" if is_home else "Away",
                "is_neutral": True,
                "opponent": opp,
                "goals_for": gf,
                "goals_against": ga,
                "result": _result(gf, ga),
                "xg_for": None,
                "xg_against": None,
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Source 2: OpenFootball Copa América TXT
# ---------------------------------------------------------------------------

_COPA_TXT_URLS = {
    2021: "https://raw.githubusercontent.com/openfootball/copa-america/master/2021--brazil/copa.txt",
}


def _parse_openfootball_txt(content: str, year: int, competition: str) -> pd.DataFrame:
    rows: list[dict] = []
    current_stage = ""

    for line in content.splitlines():
        line_s = line.strip()
        if not line_s:
            continue

        # Stage headers (e.g. "Group A", "Quarterfinal")
        if line_s.startswith("Group ") or line_s in (
            "Quarterfinal", "Semifinal", "Final",
            "Quarter-finals", "Semi-finals", "Third place",
        ):
            current_stage = line_s
            continue

        if "Argentina" not in line_s:
            continue

        # Expect a score pattern like "1-1" or "2-0"
        score_m = re.search(r"\b(\d+)\s*-\s*(\d+)\b", line_s)
        if not score_m:
            continue

        # Date at start of line: "Jun/14" or "Jun/14 18:00"
        date_m = re.match(r"(\w{3})/(\d{1,2})", line_s)
        if not date_m:
            continue

        month_str = date_m.group(1)
        day = int(date_m.group(2))
        month_num = MONTH_MAP.get(month_str)
        if not month_num:
            continue

        date = f"{year}-{month_num:02d}-{day:02d}"
        gf_raw = int(score_m.group(1))
        ga_raw = int(score_m.group(2))

        pre = line_s[:score_m.start()]
        post = line_s[score_m.end():]

        # Strip "Mon/DD HH:MM  " prefix
        pre_clean = re.sub(r"^\w{3}/\d{1,2}\s*(?:\d{2}:\d{2})?\s*", "", pre).strip()
        team1 = pre_clean

        team2 = post.split("@")[0].strip()

        if "Argentina" in team1:
            opponent = team2
            gf, ga = gf_raw, ga_raw
        elif "Argentina" in team2:
            opponent = team1
            gf, ga = ga_raw, gf_raw
        else:
            continue

        if not opponent:
            continue

        rows.append({
            "date": date,
            "competition": competition,
            "stage": current_stage,
            "venue": "Away",
            "is_neutral": True,
            "opponent": opponent,
            "goals_for": gf,
            "goals_against": ga,
            "result": _result(gf, ga),
            "xg_for": None,
            "xg_against": None,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _from_openfootball_copa(year: int, comp_label: str) -> pd.DataFrame:
    url = _COPA_TXT_URLS.get(year)
    if not url:
        return pd.DataFrame()
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        resp.encoding = "utf-8"
        df = _parse_openfootball_txt(resp.text, year, comp_label)
        logger.info("OpenFootball Copa América %d: %d Argentina matches", year, len(df))
        return df
    except Exception as exc:
        logger.warning("OpenFootball Copa América %d failed: %s", year, exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Source 3: Wikipedia CONMEBOL WCQ tables
# ---------------------------------------------------------------------------

def _parse_wikipedia_date(s: str) -> str | None:
    """Convert '7 September 2023', 'Sep 7, 2023', '2023-09-07' → 'YYYY-MM-DD'."""
    MONTHS = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
        "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    s = str(s).strip()
    if not s or s.lower() in ("nan", "none", ""):
        return None

    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return s[:10]

    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s)
    if m:
        day, mo, yr = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        month = MONTHS.get(mo)
        if month:
            return f"{yr}-{month:02d}-{day:02d}"

    m = re.match(r"(\w+)\s+(\d{1,2}),?\s+(\d{4})", s)
    if m:
        mo, day, yr = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        month = MONTHS.get(mo)
        if month:
            return f"{yr}-{month:02d}-{day:02d}"

    return None


def _clean_wiki_name(raw: str) -> str:
    return re.sub(r"\s*\[.*?\]\s*", "", str(raw)).strip()


def _from_wikipedia_wcq(wcq_year: int) -> pd.DataFrame:
    import urllib.parse

    if wcq_year == 2026:
        page_title = "2026 FIFA World Cup qualification (CONMEBOL)"
        comp_label = "World Cup Qualifying - CONMEBOL"
    else:
        page_title = "2022 FIFA World Cup qualification (CONMEBOL)"
        comp_label = "World Cup Qualifying 2022 - CONMEBOL"

    encoded_title = urllib.parse.quote(page_title)
    api_url = (
        f"https://en.wikipedia.org/w/api.php"
        f"?action=parse&page={encoded_title}&format=json&prop=text"
    )
    headers = {"User-Agent": "ScalonetaBot/1.0 (data-engineering-project)"}

    logger.info("Fetching Wikipedia WCQ %d via API …", wcq_year)
    try:
        time.sleep(2)
        resp = requests.get(api_url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            logger.warning("Wikipedia API error for WCQ %d: %s", wcq_year, data["error"].get("info"))
            return pd.DataFrame()
        html = data.get("parse", {}).get("text", {}).get("*", "")
        if not html:
            logger.warning("Wikipedia API returned empty HTML for WCQ %d", wcq_year)
            return pd.DataFrame()
    except Exception as exc:
        logger.warning("Wikipedia WCQ %d request failed: %s", wcq_year, exc)
        return pd.DataFrame()

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
    except Exception as exc:
        logger.warning("Wikipedia WCQ %d HTML parse failed: %s", wcq_year, exc)
        return pd.DataFrame()

    rows: list[dict] = []
    _DATE_PATTERN = re.compile(
        r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August"
        r"|September|October|November|December)\s+\d{4}"
    )

    for table in soup.find_all("table"):
        header_row = table.find("tr")
        if not header_row:
            continue
        ths = header_row.find_all("th")
        if len(ths) != 3:
            continue
        texts = [th.get_text(strip=True) for th in ths]
        # Wikipedia match tables: [home_team, score, away_team] as column headers
        score_m = re.match(r"^(\d+)\s*[–\-]\s*(\d+)$", texts[1])
        if not score_m:
            continue
        home = _clean_wiki_name(texts[0])
        away = _clean_wiki_name(texts[2])
        if "Argentina" not in home and "Argentina" not in away:
            continue

        hs, as_ = int(score_m.group(1)), int(score_m.group(2))
        if "Argentina" in home:
            opponent, gf, ga, is_home = away, hs, as_, True
        else:
            opponent, gf, ga, is_home = home, as_, hs, False

        if not opponent or opponent.lower() in ("nan", "none", ""):
            continue

        date_node = table.find_previous(string=_DATE_PATTERN)
        date = _parse_wikipedia_date(str(date_node).strip()) if date_node else None
        if not date or date < CUTOFF_DATE:
            continue

        rows.append({
            "date": date,
            "competition": comp_label,
            "stage": "Qualifying",
            "venue": "Home" if is_home else "Away",
            "is_neutral": False,
            "opponent": opponent,
            "goals_for": gf,
            "goals_against": ga,
            "result": _result(gf, ga),
            "xg_for": None,
            "xg_against": None,
        })

    # Deduplicate within this source
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(subset=["date", "opponent"])
    logger.info("Wikipedia WCQ %d: %d Argentina matches", wcq_year, len(df))
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def extract_argentina_matches() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    logger.info("=== Source 1: StatsBomb (WC 2022 + Copa América 2024) ===")
    sb_df = _from_statsbomb()
    if not sb_df.empty:
        frames.append(sb_df)

    logger.info("=== Source 2: OpenFootball Copa América 2021 ===")
    ca2021 = _from_openfootball_copa(2021, "Copa América 2021")
    if not ca2021.empty:
        frames.append(ca2021)

    logger.info("=== Source 3a: Wikipedia WCQ 2026 ===")
    wcq2026 = _from_wikipedia_wcq(2026)
    if not wcq2026.empty:
        frames.append(wcq2026)

    logger.info("=== Source 3b: Wikipedia WCQ 2022 ===")
    wcq2022 = _from_wikipedia_wcq(2022)
    if not wcq2022.empty:
        frames.append(wcq2022)

    if not frames:
        logger.error("No match data collected from any source!")
        return pd.DataFrame(columns=[
            "match_id", "date", "competition", "stage", "venue", "is_neutral",
            "opponent", "goals_for", "goals_against", "result", "xg_for", "xg_against",
        ])

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    combined = combined.dropna(subset=["date"])
    combined = combined[combined["date"] >= CUTOFF_DATE].copy()

    # Deduplicate: StatsBomb rows have higher priority (they come first in frames)
    combined = combined.drop_duplicates(subset=["date", "opponent"], keep="first")

    combined["match_id"] = combined.apply(
        lambda r: build_match_id(r["date"], r["opponent"]), axis=1
    )
    combined = combined.sort_values("date").reset_index(drop=True)
    logger.info("Total distinct Argentina matches: %d", len(combined))
    return combined


def save(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")
    logger.info("Saved %d rows → %s", len(df), OUT_FILE)


if __name__ == "__main__":
    df = extract_argentina_matches()
    save(df)
