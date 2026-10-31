-- ============================================================================
-- SCHEMA RELATIONNEL : BASE DE DONNÉES CAN 2025 (MAROC)
-- ============================================================================

DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS historical_afcon;

CREATE TABLE historical_afcon (
    year INTEGER PRIMARY KEY,
    host_country TEXT NOT NULL,
    winner TEXT NOT NULL,
    runner_up TEXT NOT NULL,
    num_teams INTEGER,
    matches_played INTEGER,
    total_goals INTEGER,
    goals_per_match REAL,
    avg_attendance INTEGER,
    host_won INTEGER
);

CREATE TABLE teams (
    team_id TEXT PRIMARY KEY,
    team_name TEXT NOT NULL,
    group_name TEXT NOT NULL,
    fifa_rank INTEGER,
    market_value_m_eur REAL,
    coach_style TEXT,
    confederation_region TEXT,
    previous_titles INTEGER,
    final_stage_2025 TEXT
);

CREATE TABLE matches (
    match_id TEXT PRIMARY KEY,
    match_date TEXT NOT NULL,
    stage TEXT NOT NULL,
    group_name TEXT,
    home_team_id TEXT NOT NULL,
    away_team_id TEXT NOT NULL,
    home_goals INTEGER,
    away_goals INTEGER,
    home_xg REAL,
    away_xg REAL,
    home_possession INTEGER,
    away_possession INTEGER,
    home_shots INTEGER,
    home_shots_on_target INTEGER,
    away_shots INTEGER,
    away_shots_on_target INTEGER,
    host_city TEXT,
    attendance INTEGER,
    total_goals INTEGER,
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id)
);

CREATE TABLE players (
    player_id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL,
    team_id TEXT NOT NULL,
    team_name TEXT NOT NULL,
    position TEXT NOT NULL,
    age INTEGER,
    club TEXT,
    market_value_m_eur REAL,
    matches_played INTEGER,
    minutes_played INTEGER,
    goals INTEGER,
    xg REAL,
    assists INTEGER,
    xa REAL,
    key_passes INTEGER,
    progressive_carries INTEGER,
    tackles_won INTEGER,
    interceptions INTEGER,
    duels_won_pct REAL,
    clean_sheets INTEGER,
    rating REAL,
    goals_per_90 REAL,
    assists_per_90 REAL,
    goal_contributions INTEGER,
    goal_contributions_per_90 REAL,
    xg_diff REAL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);
