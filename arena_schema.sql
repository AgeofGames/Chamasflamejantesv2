-- V24: permanent teams, immutable duel rosters and monthly individual ladders.
CREATE TABLE IF NOT EXISTS arena_teams (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, size INTEGER NOT NULL CHECK(size IN (2,3)),
 captain_id INTEGER NOT NULL REFERENCES players(id),
 archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS arena_team_members (
 team_id INTEGER NOT NULL REFERENCES arena_teams(id), player_id INTEGER NOT NULL REFERENCES players(id),
 state TEXT NOT NULL CHECK(state IN ('invited','accepted','declined','left')),
 responded_at TEXT DEFAULT '', PRIMARY KEY(team_id,player_id)
);
CREATE INDEX IF NOT EXISTS idx_arena_members_player ON arena_team_members(player_id,state);
CREATE TABLE IF NOT EXISTS arena_team_duels (
 id INTEGER PRIMARY KEY AUTOINCREMENT, team_a INTEGER NOT NULL REFERENCES arena_teams(id),
 team_b INTEGER NOT NULL REFERENCES arena_teams(id), size INTEGER NOT NULL CHECK(size IN (2,3)),
 name_a TEXT NOT NULL, name_b TEXT NOT NULL, captain_a INTEGER NOT NULL REFERENCES players(id),
 captain_b INTEGER NOT NULL REFERENCES players(id), status TEXT NOT NULL DEFAULT 'pending',
 message TEXT NOT NULL DEFAULT '', requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 responded_at TEXT DEFAULT '', finished_at TEXT DEFAULT '', match_id TEXT NOT NULL DEFAULT '',
 match_url TEXT NOT NULL DEFAULT '', match_error TEXT NOT NULL DEFAULT '', match_payload TEXT DEFAULT '',
 winner_side TEXT CHECK(winner_side IN ('a','b')), submitted_by INTEGER REFERENCES players(id),
 share_token TEXT NOT NULL UNIQUE, CHECK(team_a<>team_b)
);
CREATE TABLE IF NOT EXISTS arena_duel_members (
 duel_id INTEGER NOT NULL REFERENCES arena_team_duels(id) ON DELETE CASCADE,
 player_id INTEGER NOT NULL REFERENCES players(id), side TEXT NOT NULL CHECK(side IN ('a','b')),
 profile_id TEXT NOT NULL, PRIMARY KEY(duel_id,player_id), UNIQUE(duel_id,profile_id)
);
CREATE INDEX IF NOT EXISTS idx_arena_duel_members_player ON arena_duel_members(player_id,duel_id);
CREATE INDEX IF NOT EXISTS idx_arena_team_duel_status ON arena_team_duels(status,id DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_arena_team_match ON arena_team_duels(match_id) WHERE match_id<>'';
CREATE TABLE IF NOT EXISTS arena_match_claims (
 match_id TEXT PRIMARY KEY, queue TEXT NOT NULL, event_id INTEGER NOT NULL
);
INSERT OR IGNORE INTO arena_match_claims SELECT match_id,'x1',id FROM social_duels WHERE COALESCE(match_id,'')<>'';
CREATE TRIGGER IF NOT EXISTS arena_claim_x1_insert AFTER INSERT ON social_duels WHEN COALESCE(NEW.match_id,'')<>'' BEGIN
 INSERT INTO arena_match_claims VALUES(NEW.match_id,'x1',NEW.id);
END;
CREATE TRIGGER IF NOT EXISTS arena_claim_x1_update AFTER UPDATE OF match_id ON social_duels WHEN COALESCE(NEW.match_id,'')<>COALESCE(OLD.match_id,'') BEGIN
 DELETE FROM arena_match_claims WHERE match_id=OLD.match_id AND queue='x1' AND event_id=OLD.id;
 INSERT INTO arena_match_claims SELECT NEW.match_id,'x1',NEW.id WHERE COALESCE(NEW.match_id,'')<>'';
END;
CREATE TRIGGER IF NOT EXISTS arena_claim_x1_delete AFTER DELETE ON social_duels BEGIN
 DELETE FROM arena_match_claims WHERE queue='x1' AND event_id=OLD.id;
END;
CREATE TRIGGER IF NOT EXISTS arena_claim_team_update AFTER UPDATE OF match_id ON arena_team_duels WHEN NEW.match_id<>OLD.match_id BEGIN
 DELETE FROM arena_match_claims WHERE queue='teams' AND event_id=OLD.id;
 INSERT INTO arena_match_claims SELECT NEW.match_id,'teams',NEW.id WHERE NEW.match_id<>'';
END;
CREATE TRIGGER IF NOT EXISTS arena_claim_team_delete AFTER DELETE ON arena_team_duels BEGIN
 DELETE FROM arena_match_claims WHERE queue='teams' AND event_id=OLD.id;
END;
CREATE TABLE IF NOT EXISTS arena_seasons (season TEXT PRIMARY KEY, closed_at TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS arena_standings (
 season TEXT NOT NULL, queue TEXT NOT NULL CHECK(queue IN ('x1','2v2','3v3')),
 player_id INTEGER NOT NULL REFERENCES players(id), points INTEGER NOT NULL DEFAULT 0 CHECK(points BETWEEN 0 AND 999),
 wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0,
 loss_streak INTEGER NOT NULL DEFAULT 0, loss_bank INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(season,queue,player_id)
);
CREATE TABLE IF NOT EXISTS arena_results (
 queue TEXT NOT NULL, event_id INTEGER NOT NULL, player_id INTEGER NOT NULL REFERENCES players(id),
 season TEXT NOT NULL, won INTEGER NOT NULL, points_before INTEGER NOT NULL, points_after INTEGER NOT NULL,
 demoted INTEGER NOT NULL, recorded_at TEXT NOT NULL, PRIMARY KEY(queue,event_id,player_id)
);
CREATE INDEX IF NOT EXISTS idx_arena_results_profile ON arena_results(player_id,recorded_at DESC);
CREATE TABLE IF NOT EXISTS arena_awards (
 season TEXT NOT NULL, queue TEXT NOT NULL, player_id INTEGER NOT NULL REFERENCES players(id),
 tier INTEGER NOT NULL, points INTEGER NOT NULL, position INTEGER NOT NULL, wins INTEGER NOT NULL, losses INTEGER NOT NULL,
 PRIMARY KEY(season,queue,player_id)
);
