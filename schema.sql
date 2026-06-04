-- Rockson Performance Schema App
-- SQLite database schema

PRAGMA foreign_keys = ON;

-- PT profile / branding settings
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- Default seed data for settings
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('pt_name',  'Rockson Performance'),
    ('pt_logo',  ''),
    ('app_version', '1.0.0');

-- Muscle groups (configurable in Settings)
CREATE TABLE IF NOT EXISTS muscle_groups (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    color      TEXT NOT NULL DEFAULT '#f9b233',
    sort_order INTEGER NOT NULL DEFAULT 0,
    active     INTEGER NOT NULL DEFAULT 1
);

INSERT OR IGNORE INTO muscle_groups (name, color, sort_order) VALUES
    ('Chest',       '#ff6b35', 1),
    ('Back',        '#4fc3f7', 2),
    ('Shoulders',   '#ce93d8', 3),
    ('Biceps',      '#80cbc4', 4),
    ('Triceps',     '#ffcc02', 5),
    ('Quads',       '#ef9a9a', 6),
    ('Hamstrings',  '#f48fb1', 7),
    ('Glutes',      '#ffab91', 8),
    ('Lower Back',  '#a5d6a7', 9),
    ('Core',        '#b9f6ca', 10),
    ('Calves',      '#90caf9', 11);

-- Exercise library (shared across all clients/schedules)
CREATE TABLE IF NOT EXISTS exercises (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT NOT NULL,
    muscle_group_id  INTEGER REFERENCES muscle_groups(id) ON DELETE SET NULL,
    default_sets     INTEGER,
    default_reps     TEXT,
    image_filename   TEXT,
    is_default       INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO exercises (name, muscle_group_id, default_sets, default_reps, is_default) VALUES
    ('Barbell Bench Press',     1, 4, '6-8',   1),
    ('Incline DB Press',        1, 4, '8-10',  1),
    ('Dips',                    1, 3, '8-10',  1),
    ('Cable Fly',               1, 3, '12-15', 1),
    ('DB Bench Press',          1, 3, '10-12', 1),
    ('Barbell Row',             2, 4, '6-8',   1),
    ('Lat Pulldown',            2, 3, '8-10',  1),
    ('Pull-up / Chin-up',       2, 4, '6-10',  1),
    ('Seated Cable Row',        2, 3, '10-12', 1),
    ('One-Arm DB Row',          2, 3, '10-12', 1),
    ('DB Overhead Press',       3, 3, '8-10',  1),
    ('Arnold Press',            3, 3, '8-10',  1),
    ('Lateral Raise',           3, 3, '15-20', 1),
    ('Face Pull',               3, 3, '15-20', 1),
    ('EZ-Bar Curl',             4, 3, '10-12', 1),
    ('DB Hammer Curl',          4, 3, '10-12', 1),
    ('Incline DB Curl',         4, 3, '10-12', 1),
    ('Reverse Curl',            4, 3, '12-15', 1),
    ('Tricep Pushdown',         5, 3, '12-15', 1),
    ('Overhead Tricep Ext.',    5, 3, '12-15', 1),
    ('Skull Crusher',           5, 4, '10-12', 1),
    ('Barbell Squat',           6, 4, '6-8',   1),
    ('Leg Press',               6, 4, '10-12', 1),
    ('Hack Squat',              6, 4, '8-10',  1),
    ('Leg Extension',           6, 3, '12-15', 1),
    ('Bulgarian Split Squat',   6, 4, '8-10',  1),
    ('Walking Lunges',          6, 3, '12-15', 1),
    ('Romanian Deadlift',       7, 3, '8-10',  1),
    ('Stiff-Leg Deadlift',      7, 3, '10-12', 1),
    ('Nordic Curl',             7, 3, '8-12',  1),
    ('Seated Leg Curl',         7, 3, '12-15', 1),
    ('Deadlift',                7, 4, '5-6',   1),
    ('Hip Thrust',              8, 3, '10-12', 1),
    ('Cable Glute Kickback',    8, 3, '12-15', 1),
    ('Hip Abduction Machine',   8, 3, '15-20', 1),
    ('Back Extension',          9, 4, '10-12', 1),
    ('Dead Bug',               10, 2, '8-10',  1),
    ('Plank',                  10, 3, '30-60s',1),
    ('Cable Crunch',           10, 3, '15-20', 1),
    ('Calf Raise',             11, 4, '15-20', 1);

-- Clients
CREATE TABLE IF NOT EXISTS clients (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    notes      TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Templates (not tied to a specific client)
CREATE TABLE IF NOT EXISTS templates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO templates (name, description) VALUES
    ('Fullbody Hypertrophy', '4 days/week fullbody, focus on hypertrophy 8-15 reps'),
    ('Push / Pull / Legs',   '6 day PPL split, strength and hypertrophy'),
    ('Upper / Lower',        '4 day upper/lower split');

-- Schedules (one per client per week)
CREATE TABLE IF NOT EXISTS schedules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id   INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES templates(id) ON DELETE SET NULL,
    week_number INTEGER NOT NULL,
    year        INTEGER NOT NULL DEFAULT (strftime('%Y', 'now')),
    date_start  TEXT,
    date_end    TEXT,
    status      TEXT NOT NULL DEFAULT 'draft',   -- draft | final
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(client_id, week_number, year)
);

-- Training days within a schedule
CREATE TABLE IF NOT EXISTS schedule_days (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id   INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
    day_of_week   INTEGER NOT NULL,  -- 0=Mon, 1=Tue, ... 6=Sun
    day_label     TEXT,              -- e.g. "Dag 1", "Push A"
    sort_order    INTEGER NOT NULL DEFAULT 0
);

-- Muscle groups targeted per day (many-to-many)
CREATE TABLE IF NOT EXISTS day_muscle_groups (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_day_id INTEGER NOT NULL REFERENCES schedule_days(id) ON DELETE CASCADE,
    muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id) ON DELETE CASCADE
);

-- Exercises within a day
CREATE TABLE IF NOT EXISTS day_exercises (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_day_id INTEGER NOT NULL REFERENCES schedule_days(id) ON DELETE CASCADE,
    exercise_id     INTEGER REFERENCES exercises(id) ON DELETE SET NULL,
    custom_name     TEXT,            -- if not from library
    muscle_group_id INTEGER REFERENCES muscle_groups(id) ON DELETE SET NULL,
    set_code        TEXT,            -- e.g. A1, A2, B1 (manual)
    sets            INTEGER,
    reps            TEXT,            -- e.g. "8-10", "12", "30s"
    image_filename  TEXT,            -- per-exercise override image
    notes           TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    is_warmup       INTEGER NOT NULL DEFAULT 0
);
