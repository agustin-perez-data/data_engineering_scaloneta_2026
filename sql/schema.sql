-- =============================================================================
-- schema.sql — Argentina 2026 World Cup analytics
-- PostgreSQL DDL: dimensions, facts, events, indexes
-- =============================================================================

-- ---------------------------------------------------------------------------
-- dim_player: the 55-player extended squad
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_player (
    player_id          SERIAL       PRIMARY KEY,
    player_name        VARCHAR(100) NOT NULL,
    short_name         VARCHAR(60),
    position           VARCHAR(2)   CHECK (position IN ('GK', 'DF', 'MF', 'FW')),
    current_club       VARCHAR(100),
    current_league     VARCHAR(100),
    fbref_name         VARCHAR(100),   -- exact name as it appears in FBRef
    statsbomb_name     VARCHAR(100),   -- exact name as it appears in StatsBomb
    created_at         TIMESTAMP    DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- dim_competition: tournament / competition types
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_competition (
    competition_id     SERIAL       PRIMARY KEY,
    name               VARCHAR(100) NOT NULL,
    short_name         VARCHAR(40),
    type               VARCHAR(10)  CHECK (type IN ('WC', 'CA', 'WCQ', 'FRIENDLY')),
    year               INTEGER,
    confederation      VARCHAR(20)  DEFAULT 'CONMEBOL'
);

-- ---------------------------------------------------------------------------
-- fact_match: Argentina national team match results
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_match (
    match_id           VARCHAR(30)  PRIMARY KEY,
    date               DATE         NOT NULL,
    competition_id     INTEGER      REFERENCES dim_competition(competition_id),
    stage              VARCHAR(80),
    is_home            BOOLEAN,
    is_neutral         BOOLEAN,
    opponent           VARCHAR(60)  NOT NULL,
    goals_for          INTEGER,
    goals_against      INTEGER,
    result             CHAR(1)      CHECK (result IN ('W', 'D', 'L')),
    xg_for             DECIMAL(4,2),
    xg_against         DECIMAL(4,2),
    possession_pct     DECIMAL(4,1),
    shots              INTEGER,
    shots_on_target    INTEGER,
    venue              VARCHAR(120)
);

-- ---------------------------------------------------------------------------
-- fact_player_match: per-match player stats (outfield + GK in same table)
-- GK-specific columns (saves, save_pct, clean_sheet, psxg) are NULL for outfield
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_player_match (
    match_id            VARCHAR(30)  REFERENCES fact_match(match_id),
    player_id           INTEGER      REFERENCES dim_player(player_id),
    started             BOOLEAN,
    minutes_played      INTEGER,
    goals               INTEGER      DEFAULT 0,
    assists             INTEGER      DEFAULT 0,
    shots               INTEGER      DEFAULT 0,
    shots_on_target     INTEGER      DEFAULT 0,
    xg                  DECIMAL(4,2),
    xag                 DECIMAL(4,2),
    passes_completed    INTEGER,
    passes_attempted    INTEGER,
    pass_pct            DECIMAL(4,1),
    progressive_passes  INTEGER,
    key_passes          INTEGER,
    progressive_carries INTEGER,
    tackles             INTEGER      DEFAULT 0,
    interceptions       INTEGER      DEFAULT 0,
    blocks              INTEGER      DEFAULT 0,
    yellow_cards        INTEGER      DEFAULT 0,
    red_cards           INTEGER      DEFAULT 0,
    -- GK-only
    saves               INTEGER,
    save_pct            DECIMAL(4,1),
    clean_sheet         BOOLEAN,
    psxg                DECIMAL(4,2),
    PRIMARY KEY (match_id, player_id)
);

-- ---------------------------------------------------------------------------
-- fact_player_club_season: latest club season aggregated stats
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_player_club_season (
    player_id           INTEGER      REFERENCES dim_player(player_id),
    season              VARCHAR(10)  NOT NULL,
    club                VARCHAR(100) NOT NULL,
    league              VARCHAR(100) NOT NULL,
    matches_played      INTEGER      DEFAULT 0,
    starts              INTEGER      DEFAULT 0,
    minutes             INTEGER      DEFAULT 0,
    goals               INTEGER      DEFAULT 0,
    assists             INTEGER      DEFAULT 0,
    xg                  DECIMAL(5,2),
    xag                 DECIMAL(5,2),
    shots               INTEGER      DEFAULT 0,
    shots_on_target     INTEGER      DEFAULT 0,
    pass_pct            DECIMAL(4,1),
    progressive_passes  INTEGER      DEFAULT 0,
    progressive_carries INTEGER      DEFAULT 0,
    tackles             INTEGER      DEFAULT 0,
    interceptions       INTEGER      DEFAULT 0,
    yellow_cards        INTEGER      DEFAULT 0,
    red_cards           INTEGER      DEFAULT 0,
    -- GK-only
    saves               INTEGER,
    save_pct            DECIMAL(4,1),
    clean_sheets        INTEGER,
    goals_against_gk    INTEGER,
    PRIMARY KEY (player_id, season, club)
);

-- ---------------------------------------------------------------------------
-- event_statsbomb: touch / pass / shot events for heatmaps
-- Source: StatsBomb open-data (Qatar 2022, Copa América 2021)
-- Pitch coordinates: x ∈ [0,120], y ∈ [0,80] (StatsBomb standard)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS event_statsbomb (
    event_id           UUID         PRIMARY KEY,
    match_id           VARCHAR(30)  REFERENCES fact_match(match_id),
    player_id          INTEGER      REFERENCES dim_player(player_id),
    event_type         VARCHAR(40)  NOT NULL,
    period             SMALLINT,
    minute             SMALLINT,
    second             SMALLINT,
    x                  DECIMAL(5,2),
    y                  DECIMAL(5,2),
    end_x              DECIMAL(5,2),
    end_y              DECIMAL(5,2),
    outcome            VARCHAR(40),
    xg                 DECIMAL(5,3)
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_fact_match_date        ON fact_match(date);
CREATE INDEX IF NOT EXISTS idx_fact_match_competition ON fact_match(competition_id);
CREATE INDEX IF NOT EXISTS idx_fact_match_opponent    ON fact_match(opponent);

CREATE INDEX IF NOT EXISTS idx_player_match_player    ON fact_player_match(player_id);
CREATE INDEX IF NOT EXISTS idx_player_match_match     ON fact_player_match(match_id);

CREATE INDEX IF NOT EXISTS idx_player_club_player     ON fact_player_club_season(player_id);

CREATE INDEX IF NOT EXISTS idx_event_match            ON event_statsbomb(match_id);
CREATE INDEX IF NOT EXISTS idx_event_player           ON event_statsbomb(player_id);
CREATE INDEX IF NOT EXISTS idx_event_type             ON event_statsbomb(event_type);
