"""Schéma SQLite (SPEC_V2 §5). Migrations numérotées, appliquées dans l'ordre via PRAGMA user_version.
M1 : tables de données. M2 : journal des lancements d'analyse. M3 : registre d'hypothèses. Les tables d'hypothèses (M3) et de
simulation (M4) arriveront avec leurs jalons, chacune dans une migration propre."""

MIGRATION_1 = """
CREATE TABLE games (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    k INTEGER NOT NULL CHECK (k > 0),
    n_max INTEGER NOT NULL CHECK (n_max >= k),
    bonus_range INTEGER,
    bonus_exclusive INTEGER NOT NULL DEFAULT 1 CHECK (bonus_exclusive IN (0, 1)),
    notes TEXT
);

CREATE TABLE draws (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id),
    draw_date TEXT NOT NULL,
    source_draw_no INTEGER,
    numbers_json TEXT NOT NULL,
    bonus INTEGER,
    source TEXT NOT NULL,
    source_ref TEXT,
    ingested_at TEXT NOT NULL,
    row_sha256 TEXT NOT NULL UNIQUE
);
CREATE INDEX idx_draws_game_date ON draws (game_id, draw_date);

CREATE TABLE draw_corrections (
    id INTEGER PRIMARY KEY,
    draw_id INTEGER NOT NULL REFERENCES draws(id),
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT NOT NULL,
    author TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE TRIGGER draws_no_update BEFORE UPDATE ON draws
BEGIN SELECT RAISE(ABORT, 'draws is append-only: record a draw_corrections row instead'); END;
CREATE TRIGGER draws_no_delete BEFORE DELETE ON draws
BEGIN SELECT RAISE(ABORT, 'draws is append-only'); END;
CREATE TRIGGER corrections_no_update BEFORE UPDATE ON draw_corrections
BEGIN SELECT RAISE(ABORT, 'draw_corrections is append-only'); END;
CREATE TRIGGER corrections_no_delete BEFORE DELETE ON draw_corrections
BEGIN SELECT RAISE(ABORT, 'draw_corrections is append-only'); END;
"""

MIGRATION_2 = """
CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id),
    started_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    git_commit TEXT,
    dataset_hash TEXT NOT NULL,
    n_draws INTEGER NOT NULL,
    config_json TEXT NOT NULL
);

CREATE TABLE test_results (
    id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
    label TEXT NOT NULL,
    statistic REAL,
    p_raw REAL,
    p_adjusted REAL,
    method TEXT,
    family_size INTEGER,
    tag TEXT NOT NULL CHECK (tag IN ('CONFIRMATORY', 'DESCRIPTIVE')),
    detail_json TEXT
);
CREATE INDEX idx_results_run ON test_results (run_id);

CREATE TRIGGER runs_no_update BEFORE UPDATE ON analysis_runs
BEGIN SELECT RAISE(ABORT, 'analysis_runs is append-only'); END;
CREATE TRIGGER runs_no_delete BEFORE DELETE ON analysis_runs
BEGIN SELECT RAISE(ABORT, 'analysis_runs is append-only'); END;
CREATE TRIGGER results_no_update BEFORE UPDATE ON test_results
BEGIN SELECT RAISE(ABORT, 'test_results is append-only'); END;
CREATE TRIGGER results_no_delete BEFORE DELETE ON test_results
BEGIN SELECT RAISE(ABORT, 'test_results is append-only'); END;
"""

MIGRATION_3 = """
CREATE TABLE hypotheses (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES games(id),
    code TEXT NOT NULL,
    h0 TEXT NOT NULL,
    h1 TEXT NOT NULL,
    test_name TEXT NOT NULL,
    test_params_json TEXT NOT NULL,
    correction TEXT NOT NULL CHECK (correction IN ('none', 'bonferroni')),
    family_size INTEGER NOT NULL DEFAULT 1 CHECK (family_size >= 1),
    kind TEXT NOT NULL CHECK (kind IN ('PRE_REGISTERED', 'EXPLORATORY', 'POST_HOC')),
    registered_at TEXT NOT NULL,
    registered_date TEXT NOT NULL,
    n_star INTEGER CHECK (n_star IS NULL OR n_star > 0),
    UNIQUE (game_id, code)
);

CREATE TABLE hypothesis_outcomes (
    id INTEGER PRIMARY KEY,
    hypothesis_id INTEGER NOT NULL UNIQUE REFERENCES hypotheses(id),
    tested_at TEXT NOT NULL,
    n_draws_used INTEGER NOT NULL,
    statistic REAL,
    p_value REAL,
    alpha_effective REAL NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('CONFIRMED', 'NOT_CONFIRMED')),
    detail_json TEXT
);

ALTER TABLE test_results ADD COLUMN hypothesis_id INTEGER REFERENCES hypotheses(id);

CREATE TRIGGER results_confirmatory_needs_hypothesis BEFORE INSERT ON test_results
WHEN NEW.tag = 'CONFIRMATORY' AND NEW.hypothesis_id IS NULL
BEGIN SELECT RAISE(ABORT, 'a CONFIRMATORY result requires a pre-registered hypothesis'); END;

CREATE TRIGGER hypotheses_no_update BEFORE UPDATE ON hypotheses
BEGIN SELECT RAISE(ABORT, 'hypotheses is append-only'); END;
CREATE TRIGGER hypotheses_no_delete BEFORE DELETE ON hypotheses
BEGIN SELECT RAISE(ABORT, 'hypotheses is append-only'); END;
CREATE TRIGGER outcomes_no_update BEFORE UPDATE ON hypothesis_outcomes
BEGIN SELECT RAISE(ABORT, 'hypothesis_outcomes is append-only'); END;
CREATE TRIGGER outcomes_no_delete BEFORE DELETE ON hypothesis_outcomes
BEGIN SELECT RAISE(ABORT, 'hypothesis_outcomes is append-only'); END;
"""

MIGRATIONS = [MIGRATION_1, MIGRATION_2, MIGRATION_3]
