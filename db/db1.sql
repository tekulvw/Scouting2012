CREATE TABLE base_team (
    id INTEGER PRIMARY KEY,
    name TEXT,
    scoreRD1 INTEGER,
    scoreRD2 INTEGER,
    scoreRD3 INTEGER,
    scoreRD4 INTEGER,
    scoreRD5 INTEGER,
    blocking INTEGER,
    ramp INTEGER,
    defense INTEGER,
    autonomous INTEGER
);

CREATE TABLE round_stat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_number INTEGER,
    team_id INTEGER,
    topleft INTEGER,
    topmid INTEGER,
    topright INTEGER,
    midleft INTEGER,
    midmid INTEGER,
    midright INTEGER,
    botleft INTEGER,
    botmid INTEGER,
    botright INTEGER
);

CREATE TABLE full_team (
    id INTEGER PRIMARY KEY,
    round1_id INTEGER,
    round2_id INTEGER,
    round3_id INTEGER,
    round4_id INTEGER,
    round5_id INTEGER
);
