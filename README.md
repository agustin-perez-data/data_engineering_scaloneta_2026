# 🇦🇷 Scaloneta 2026 — Argentina NT Analytics

Data engineering & analytics platform tracking Argentina's national team journey to the 2026 World Cup.

---

## Stack

| Layer | Technology |
|---|---|
| Ingestion | Python (StatsBomb, Sofascore, FBRef, Wikipedia) |
| Storage | PostgreSQL 15 |
| Transformation | Pandas + custom ETL pipeline |
| BI / Dashboards | Metabase |
| Advanced visuals | Streamlit + mplsoccer |
| Orchestration | Docker Compose |

---

## Architecture

```
Data Sources                   ETL Pipeline              Outputs
────────────                   ────────────              ───────
StatsBomb open data  ──►  Extract  ──►  Transform  ──►  PostgreSQL
Sofascore API        ──►  (raw CSV)    (clean CSV)       │
FBRef / Wikipedia    ──►                                  ├─► Metabase dashboards
                                                          └─► Streamlit app
```

---

## Data Coverage

| Source | Competitions | Stats |
|---|---|---|
| StatsBomb | WC 2022, Copa América 2024 | Event-level: shots (xG), passes, carries, duels |
| Sofascore NT | Copa América 2021, WCQ 2022/2026 | Per-match: goals, assists, tackles, passes |
| Understat | Big 5 club leagues 2024-25 | Goals, assists, xG, xAG, shots |
| Sofascore club | ARG, BRA, MLS, POR 2024-25 | Goals, assists, xG, xAG, tackles, pass% |
| Sofascore Big5 | EPL, La Liga, Serie A, Ligue 1, Bundesliga | Tackles, interceptions, pass%, GK stats |

---

## Database Schema

```
dim_player          (26 rows)  — squad metadata
dim_competition     (5 rows)   — WC / Copa América / WCQ
fact_match          (55 rows)  — match results 2021–2025
fact_player_match   (764 rows) — per-player per-match stats
fact_player_club_season (26)   — club season stats 2024-25
event_statsbomb  (23,266 rows) — granular shot/pass/carry events
```

---

## Streamlit App

Three interactive pitch visualizations at `localhost:8501`:

- **🎯 Shot Map** — StatsBomb shots with xG, filterable by player / competition / match
- **🔥 Heat Map** — KDE activity map by event type (passes, carries, defensive actions)
- **🔵 Pass Map** — Pass lines with direction arrows, 4 pass-type filters

All pages support **English / Spanish** toggle.

---

## Metabase Dashboards

Three BI dashboards at `localhost:3000`:

1. **Plantel 2024-25** — Club stats, xG vs goals scatter, tackles/interceptions rankings
2. **Selección — Resultados** — Match history, W/D/L by competition, goals trend
3. **Selección — Jugadores** — Individual NT performance, xG vs goals, defensive rankings

---

## Quick Start

### Prerequisites
- Docker Desktop
- 4 GB RAM recommended

### 1. Clone & configure

```bash
git clone https://github.com/yourusername/data_engineering_scaloneta_2026.git
cd data_engineering_scaloneta_2026
cp .env.example .env
```

### 2. Start services

```bash
docker compose up -d
```

Services: PostgreSQL (5432), Metabase (3000), Streamlit (8501), ETL runner.

### 3. Run the ETL pipeline

```bash
# Extract all data sources
docker exec scaloneta_etl python -m etl.extract.run_extract

# Transform to clean schema
docker exec scaloneta_etl python -m etl.transform.run_transform

# Load to PostgreSQL
docker exec scaloneta_etl python -m etl.load.run_all
```

### 4. Setup Metabase dashboards

```bash
docker exec scaloneta_etl python scripts/setup_metabase.py
```

---

## Project Structure

```
├── config/
│   └── players.py              # 26-player squad definition
├── etl/
│   ├── extract/                # Data ingestion (6 sources)
│   ├── transform/              # Cleaning & schema mapping
│   └── load/                   # PostgreSQL loaders
├── streamlit/
│   ├── app.py                  # Navigation + theme
│   ├── i18n.py                 # ES/EN translations
│   └── pages/
│       ├── 03_Shot_Map.py
│       ├── 04_Heatmap.py
│       └── 05_Pass_Map.py
├── scripts/
│   └── setup_metabase.py       # Auto-creates Metabase dashboards
├── sql/
│   └── schema.sql              # PostgreSQL DDL
├── data/
│   └── raw/                    # Raw CSVs from extractors
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## Data Sources

- **StatsBomb** open data (free) — [github.com/statsbomb/open-data](https://github.com/statsbomb/open-data)
- **Sofascore** unofficial API
- **Understat** via [soccerdata](https://github.com/probberechts/soccerdata)
- **Wikipedia** match results via MediaWiki API
