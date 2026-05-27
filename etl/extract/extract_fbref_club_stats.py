"""
etl/extract/extract_fbref_club_stats.py
-----------------------------------------
Latest-season club stats for all squad players.

- Big 5 leagues    → Understat via soccerdata (unchanged)
- Non-Big5 leagues → ESPN unofficial API (sports.core.api.espn.com)
                     soccerdata only supports Big5; FBRef blocks scraping.
                     ESPN provides career stats at the league level:
                     goals, assists, tackles, interceptions, pass_pct,
                     appearances, cards, and GK stats.
- Fallback         → stub rows (all nulls) if ESPN also fails

Output: data/raw/club_stats_all_leagues.csv
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from etl.extract.utils import flatten_soccerdata, normalize_name  # noqa: E402
from config.players import SQUAD, LEAGUE_SEASON, BIG5_LEAGUES  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

OUT_DIR = PROJECT_ROOT / "data" / "raw"
OUT_FILE = OUT_DIR / "club_stats_all_leagues.csv"

SQUAD_NAMES_NORM: set[str] = {normalize_name(p["player_name"]) for p in SQUAD}

# Understat league code → soccerdata league code
UNDERSTAT_LEAGUES = {
    "ENG-Premier League": "ENG-Premier League",
    "ESP-La Liga":        "ESP-La Liga",
    "ITA-Serie A":        "ITA-Serie A",
    "FRA-Ligue 1":        "FRA-Ligue 1",
    "GER-Bundesliga":     "GER-Bundesliga",
}

# Club name overrides: our config name → ESPN display name
CLUB_ESPN_OVERRIDES: dict[str, str] = {
    "Union Saint-Gilloise": "Union St.-Gilloise",
    "Hamburger SV":         "Hamburg SV",
}

# ESPN league slugs — covers both Big5 (as fallback) and non-Big5
ESPN_LEAGUE_SLUGS: dict[str, str] = {
    # Big 5 (used as fallback when Understat misses a player)
    "ENG-Premier League":      "eng.1",
    "ESP-La Liga":             "esp.1",
    "ITA-Serie A":             "ita.1",
    "FRA-Ligue 1":             "fra.1",
    "GER-Bundesliga":          "ger.1",
    # Non-Big5 (primary source)
    "ARG-Liga Profesional":    "arg.1",
    "BRA-Série A":             "bra.1",
    "USA-Major League Soccer": "usa.1",
    "POR-Primeira Liga":       "por.1",
    "GER-2. Bundesliga":       "ger.2",
    "BEL-First Division A":    "bel.1",
}

# ESPN stat name → our schema column
# ESPN career stats at the league (not strictly one season, but informative)
ESPN_STAT_SCHEMA: dict[str, str] = {
    # Offensive
    "totalGoals":     "goals",
    "goalAssists":    "assists",
    "totalShots":     "shots",          # may or may not exist; calc fallback below
    "shotsOnGoal":    "shots_on_target",
    # General
    "appearances":    "matches_played",
    "yellowCards":    "yellow_cards",
    "redCards":       "red_cards",
    # Defensive
    "totalTackles":   "tackles",
    "interceptions":  "interceptions",
    # GK
    "totalSaves":     "saves",
    "savePercentage": "save_pct",
    "cleanSheets":    "clean_sheets",
    "goalsAgainst":   "goals_against_gk",
}

FINAL_COLS = [
    "player_name", "team", "league", "season",
    "matches_played", "starts", "minutes",
    "goals", "assists", "xg", "xag",
    "shots", "shots_on_target",
    "pass_pct", "progressive_passes", "progressive_carries",
    "tackles", "interceptions",
    "yellow_cards", "red_cards",
    "saves", "save_pct", "clean_sheets", "goals_against_gk",
]

_ESPN_SESSION: Optional[requests.Session] = None


def _safe_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _find_col(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


# ---------------------------------------------------------------------------
# Understat (Big 5)
# ---------------------------------------------------------------------------

def _scrape_understat(league: str, season: str) -> Optional[pd.DataFrame]:
    """Fetch player season stats from Understat via soccerdata."""
    try:
        import soccerdata as sd
    except ImportError:
        logger.error("soccerdata not installed")
        return None

    logger.info("Understat: %s  %s", league, season)
    try:
        src = sd.Understat(leagues=league, seasons=season)
        df = src.read_player_season_stats()
    except Exception as exc:
        logger.warning("Understat %s/%s failed: %s", league, season, exc)
        return None

    df = flatten_soccerdata(df)
    logger.info("  raw shape: %s  columns: %s", df.shape, list(df.columns[:15]))

    player_col = _find_col(df, "player", "player_name", "players", "name")
    if player_col is None:
        logger.warning("  Cannot find player column in Understat data for %s", league)
        return None

    mask = df[player_col].apply(lambda n: normalize_name(str(n)) in SQUAD_NAMES_NORM)
    df = df[mask].copy()
    if df.empty:
        logger.info("  No squad players found in %s", league)
        return None

    renames: dict[str, str] = {}

    def _try(*candidates: str, out: str) -> None:
        for c in candidates:
            if c in df.columns:
                renames[c] = out
                break

    _try("player", "player_name", "players", "name", out="player_name")
    _try("team", "squad", "club", out="team")
    _try("season", "year", out="season")
    _try("games", "matches", "mp", "games_played", out="matches_played")
    _try("time", "minutes", "min", out="minutes")
    _try("goals", "gls", out="goals")
    _try("xg", "expected_goals", "npxg", out="xg")
    _try("assists", "ast", out="assists")
    _try("xa", "xag", "expected_assists", out="xag")
    _try("shots", "sh", out="shots")
    _try("key_passes", "kp", out="shots_on_target")  # Understat has key_passes not SOT
    _try("yellow", "crdy", "yel", out="yellow_cards")
    _try("red", "crdr", "red_cards_x", out="red_cards")

    df = df.rename(columns=renames)

    if "player_name" not in df.columns and player_col in df.columns:
        df = df.rename(columns={player_col: "player_name"})

    df["league"] = league
    if "season" not in df.columns:
        df["season"] = season

    logger.info("  Found %d squad players in %s", len(df), league)
    return df


# ---------------------------------------------------------------------------
# ESPN (non-Big5)
# ---------------------------------------------------------------------------

def _espn_session() -> requests.Session:
    global _ESPN_SESSION
    if _ESPN_SESSION is None:
        _ESPN_SESSION = requests.Session()
        _ESPN_SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        })
    return _ESPN_SESSION


def _espn_get(url: str, pause: float = 1.0) -> Optional[dict]:
    time.sleep(pause)
    try:
        resp = _espn_session().get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("ESPN GET failed %s — %s", url, exc)
        return None


def _espn_teams(league_slug: str) -> dict[str, tuple[str, str]]:
    """Return {normalized_name: (display_name, team_id)} for all teams."""
    data = _espn_get(
        f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams"
    )
    if not data:
        return {}
    teams = (
        data.get("sports", [{}])[0]
            .get("leagues", [{}])[0]
            .get("teams", [])
    )
    result: dict[str, tuple[str, str]] = {}
    for t in teams:
        team = t.get("team", {})
        name = team.get("displayName", "")
        tid = team.get("id", "")
        if name and tid:
            result[normalize_name(name)] = (name, str(tid))
    return result


def _espn_find_team(
    teams: dict[str, tuple[str, str]], club: str
) -> Optional[tuple[str, str]]:
    """Find a team entry by normalized name or 2-word overlap."""
    club = CLUB_ESPN_OVERRIDES.get(club, club)
    norm = normalize_name(club)
    if norm in teams:
        return teams[norm]
    club_words = set(norm.split())
    for key, val in teams.items():
        common = club_words & set(key.split())
        if len(common) >= min(2, len(club_words)):
            return val
    return None


def _espn_roster(league_slug: str, team_id: str) -> dict[str, str]:
    """Return {normalized_player_name: athlete_id}."""
    data = _espn_get(
        f"https://site.api.espn.com/apis/site/v2/sports/soccer"
        f"/{league_slug}/teams/{team_id}/roster"
    )
    if not data:
        return {}
    result: dict[str, str] = {}
    for athlete in data.get("athletes", []):
        name = athlete.get("displayName", "")
        aid = athlete.get("id", "")
        if name and aid:
            result[normalize_name(name)] = str(aid)
    return result


def _espn_find_athlete(roster: dict[str, str], player_name: str) -> Optional[str]:
    """Match a squad player name to an ESPN athlete ID."""
    norm = normalize_name(player_name)
    if norm in roster:
        return roster[norm]
    # Last-name fallback
    last = norm.split()[-1] if norm.split() else ""
    if last:
        matches = {k: v for k, v in roster.items() if last in k.split()}
        if len(matches) == 1:
            return list(matches.values())[0]
    return None


def _espn_athlete_stats(league_slug: str, athlete_id: str) -> dict[str, float]:
    """Return flat {stat_name: value} from ESPN career stats at this league."""
    data = _espn_get(
        f"https://sports.core.api.espn.com/v2/sports/soccer"
        f"/leagues/{league_slug}/athletes/{athlete_id}/statistics"
    )
    if not data:
        return {}

    flat: dict[str, float] = {}
    for cat in data.get("splits", {}).get("categories", []):
        for stat in cat.get("stats", []):
            name = stat.get("name", "")
            value = stat.get("value")
            if name and value is not None:
                flat[name] = float(value)

    # Derived stats
    if "passPct" in flat:
        flat["pass_pct_derived"] = flat["passPct"] * 100

    if "appearances" in flat and "subIns" in flat:
        flat["starts_derived"] = flat["appearances"] - flat["subIns"]

    # Total shots from left + right + headed foot shots if totalShots missing
    if "totalShots" not in flat:
        foot_shots = (
            flat.get("leftFootedShots", 0)
            + flat.get("rightFootedShots", 0)
            + flat.get("headedShots", 0)
        )
        if foot_shots > 0:
            flat["totalShots"] = foot_shots

    # shots on target from total - off target if not directly available
    if "shotsOnGoal" not in flat and "totalShots" in flat and "shotsOffTarget" in flat:
        sot = flat["totalShots"] - flat["shotsOffTarget"]
        if sot >= 0:
            flat["shotsOnGoal"] = sot

    return flat


def _scrape_espn(league: str, season: str) -> Optional[pd.DataFrame]:
    """
    ESPN-based club stats for a non-Big5 league.
    Provides career totals at the league level (not strictly 2025 only),
    covering goals, assists, tackles, interceptions, pass_pct, cards, GK stats.
    """
    league_slug = ESPN_LEAGUE_SLUGS.get(league)
    if not league_slug:
        logger.warning("No ESPN slug configured for: %s", league)
        return None

    squad_in_league = [p for p in SQUAD if p["league"] == league]
    logger.info("ESPN: %s (%s) — %d squad players", league, league_slug, len(squad_in_league))

    teams = _espn_teams(league_slug)
    if not teams:
        logger.warning("ESPN: no teams found for %s", league_slug)
        return None

    rosters_cache: dict[str, dict[str, str]] = {}
    rows: list[dict] = []

    for player in squad_in_league:
        team_entry = _espn_find_team(teams, player["club"])
        if not team_entry:
            logger.warning("ESPN: team not found — %s / %s", player["player_name"], player["club"])
            continue

        team_id = team_entry[1]
        if team_id not in rosters_cache:
            rosters_cache[team_id] = _espn_roster(league_slug, team_id)
        roster = rosters_cache[team_id]

        athlete_id = _espn_find_athlete(roster, player["player_name"])
        if not athlete_id:
            logger.warning("ESPN: athlete not found — %s", player["player_name"])
            continue

        espn_stats = _espn_athlete_stats(league_slug, athlete_id)
        if not espn_stats:
            logger.warning("ESPN: no stats — %s", player["player_name"])
            continue

        row: dict = {
            "player_name": player["player_name"],
            "team":        player["club"],
            "league":      league,
            "season":      season,
        }

        # Map ESPN stats to schema
        for espn_key, schema_col in ESPN_STAT_SCHEMA.items():
            if espn_key in espn_stats:
                row[schema_col] = espn_stats[espn_key]

        # Derived stats
        if "pass_pct_derived" in espn_stats:
            row["pass_pct"] = espn_stats["pass_pct_derived"]
        if "starts_derived" in espn_stats:
            row["starts"] = espn_stats["starts_derived"]

        rows.append(row)
        logger.info(
            "  ESPN: %-25s  apps=%s  goals=%s  assists=%s  tackles=%s",
            player["player_name"],
            int(espn_stats.get("appearances", 0)),
            int(espn_stats.get("totalGoals", 0)),
            int(espn_stats.get("goalAssists", 0)),
            int(espn_stats.get("totalTackles", 0)),
        )

    if not rows:
        logger.warning("ESPN: no rows collected for %s", league)
        return None

    df = pd.DataFrame(rows)
    logger.info("ESPN %s: %d players", league, len(df))
    return df


# ---------------------------------------------------------------------------
# Stub fallback
# ---------------------------------------------------------------------------

def _make_stub_rows(players: list[dict]) -> pd.DataFrame:
    """Null rows for players whose league returned no data from any source."""
    rows = [
        {
            "player_name": p["player_name"],
            "team":        p["club"],
            "league":      p["league"],
            "season":      LEAGUE_SEASON.get(p["league"], "2024-25"),
            **{col: None for col in FINAL_COLS
               if col not in ("player_name", "team", "league", "season")},
        }
        for p in players
    ]
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def extract_club_stats() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    covered_names: set[str] = set()  # normalized names collected so far

    # Big 5 — Understat (season-accurate xG stats)
    for league in BIG5_LEAGUES:
        season = LEAGUE_SEASON.get(league, "2024-25")
        df = _scrape_understat(league, season)
        if df is not None and not df.empty:
            frames.append(df)
            covered_names.update(df["player_name"].apply(normalize_name))

    # Big5 ESPN fallback — any squad player in a Big5 league not found by Understat
    big5_missing: dict[str, list[dict]] = {}
    for p in SQUAD:
        if p["league"] in BIG5_LEAGUES and normalize_name(p["player_name"]) not in covered_names:
            big5_missing.setdefault(p["league"], []).append(p)

    if big5_missing:
        for league, players in sorted(big5_missing.items()):
            logger.info(
                "ESPN fallback for %d Big5 players not in Understat (%s): %s",
                len(players), league, [p["player_name"] for p in players],
            )
            season = LEAGUE_SEASON.get(league, "2024-25")
            # Temporarily replace SQUAD-subset for _scrape_espn by monkey-patching
            # the league filter — simpler: call helper directly per player
            espn_slug = ESPN_LEAGUE_SLUGS.get(league)
            if not espn_slug:
                logger.warning("No ESPN slug for Big5 league %s", league)
                frames.append(_make_stub_rows(players))
                continue

            teams = _espn_teams(espn_slug)
            if not teams:
                frames.append(_make_stub_rows(players))
                continue

            rosters_cache: dict[str, dict[str, str]] = {}
            rows: list[dict] = []
            for player in players:
                team_entry = _espn_find_team(teams, player["club"])
                if not team_entry:
                    logger.warning("ESPN fallback: team not found — %s / %s", player["player_name"], player["club"])
                    continue
                team_id = team_entry[1]
                if team_id not in rosters_cache:
                    rosters_cache[team_id] = _espn_roster(espn_slug, team_id)
                roster = rosters_cache[team_id]
                athlete_id = _espn_find_athlete(roster, player["player_name"])
                if not athlete_id:
                    logger.warning("ESPN fallback: athlete not found — %s", player["player_name"])
                    continue
                espn_stats = _espn_athlete_stats(espn_slug, athlete_id)
                if not espn_stats:
                    continue
                row: dict = {
                    "player_name": player["player_name"],
                    "team":        player["club"],
                    "league":      league,
                    "season":      season,
                }
                for espn_key, schema_col in ESPN_STAT_SCHEMA.items():
                    if espn_key in espn_stats:
                        row[schema_col] = espn_stats[espn_key]
                if "pass_pct_derived" in espn_stats:
                    row["pass_pct"] = espn_stats["pass_pct_derived"]
                if "starts_derived" in espn_stats:
                    row["starts"] = espn_stats["starts_derived"]
                rows.append(row)
                logger.info(
                    "  ESPN fallback: %-25s  apps=%s  goals=%s",
                    player["player_name"],
                    int(espn_stats.get("appearances", 0)),
                    int(espn_stats.get("totalGoals", 0)),
                )
            if rows:
                frames.append(pd.DataFrame(rows))
            # stub for any still-missing
            found_names = {normalize_name(r["player_name"]) for r in rows}
            still_missing = [p for p in players if normalize_name(p["player_name"]) not in found_names]
            if still_missing:
                logger.warning("ESPN fallback also missed: %s", [p["player_name"] for p in still_missing])
                frames.append(_make_stub_rows(still_missing))

    # Non-Big5 — ESPN with stub fallback
    non_big5_leagues = sorted({p["league"] for p in SQUAD if p["league"] not in BIG5_LEAGUES})
    for league in non_big5_leagues:
        season = LEAGUE_SEASON.get(league, "2024-25")
        df = _scrape_espn(league, season)
        if df is not None and not df.empty:
            frames.append(df)
        else:
            players_in_league = [p for p in SQUAD if p["league"] == league]
            logger.warning(
                "ESPN failed for %s — stub rows for %d players",
                league, len(players_in_league),
            )
            stubs = _make_stub_rows(players_in_league)
            if not stubs.empty:
                frames.append(stubs)

    if not frames:
        logger.error("No club stats collected")
        return pd.DataFrame(columns=FINAL_COLS)

    combined = pd.concat(frames, ignore_index=True)

    for col in FINAL_COLS:
        if col not in combined.columns:
            combined[col] = None

    num_cols = [c for c in FINAL_COLS if c not in ("player_name", "team", "league", "season")]
    for col in num_cols:
        combined[col] = _safe_float(combined[col])

    combined = combined[FINAL_COLS].reset_index(drop=True)
    logger.info("Club stats final shape: %s", combined.shape)
    return combined


def save(df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8")
    logger.info("Saved %d rows to %s", len(df), OUT_FILE)


if __name__ == "__main__":
    df = extract_club_stats()
    save(df)
