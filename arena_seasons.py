"""Transactional ranking ledger. Season boundaries use the Brasília calendar."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import arena_rules

ZONE = ZoneInfo('America/Sao_Paulo')
TIERS = (
 ('Brasa','#c79a72'), ('Chama','#f2a455'), ('Forja','#ef884b'),
 ('Guardião','#d3b278'), ('Guerreiro','#83cfff'), ('Conquistador','#74cd9d'),
 ('Herói','#8ebaff'), ('Lenda','#b59af5'), ('Titã','#fb8a52'), ('Imortal','#b4e2ff'),
)
# Artwork matched to the names printed on the ten supplied badges.
BADGE_SLUGS = ('brasa', 'chama', 'forja', 'guardiao', 'guerreiro',
               'conquistador', 'heroi', 'lenda', 'tita', 'imortal')
QUEUES = {'x1':'X1', '2v2':'Duplas', '3v3':'Trios'}

def utc_now():
    return datetime.now(timezone.utc)

def period(value=None):
    value = value or utc_now()
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z','+00:00'))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZONE).strftime('%Y-%m')

def badge(points):
    level = min(9, max(0, int(points)) // 100)
    return dict(level=level+1, name=TIERS[level][0], color=TIERS[level][1],
                image=f'arena/emblemas/{BADGE_SLUGS[level]}.webp',
                thumbnail=f'arena/emblemas/{BADGE_SLUGS[level]}-96.webp',
                progress=min(100, int(points)%100) if level<9 else 100)

def standing_badge(row):
    return badge(row['emblem_points'])

def close_seasons(db, current=None):
    current = current or period()
    for row in db.execute("SELECT season FROM arena_seasons WHERE season<? AND closed_at=''", (current,)).fetchall():
        db.execute('''INSERT OR IGNORE INTO arena_awards
          SELECT season,queue,player_id,MIN(9,emblem_points/100)+1,points,
            ROW_NUMBER() OVER(PARTITION BY queue ORDER BY points DESC,wins DESC,losses,player_id),wins,losses
          FROM arena_standings WHERE season=? AND wins+losses>0''', (row['season'],))
        db.execute("UPDATE arena_seasons SET closed_at=CURRENT_TIMESTAMP WHERE season=?", (row['season'],))


def result_progress(old, won, delta):
    """One calculation for new results and historical score repairs."""
    points = max(0, old['points'] + delta)
    emblem_points = min(999, max(0, old['emblem_points'] + delta))
    streak = 0 if won else old['loss_streak']+1
    bank = old['loss_bank'] if won else old['loss_bank']+1
    if not won and (streak>=3 or bank>=4):
        # A natural demotion on this loss already satisfies the penalty.
        emblem_points = min(emblem_points,max(0,(old['emblem_points']//100)*100-1))
        streak = bank = 0
    return dict(points=points, score_balance=points, emblem_points=emblem_points,
                wins=old['wins']+int(won), losses=old['losses']+int(not won),
                loss_streak=streak, loss_bank=bank,
                demoted=int(emblem_points//100 < old['emblem_points']//100))


def record_result(db, queue, event_id, winners, losers, when=None):
    """Caller owns the transaction: the match and all its points commit together."""
    when = when or utc_now().isoformat()
    season = period(when)
    winners, losers = set(winners), set(losers)
    if queue not in QUEUES or not winners or not losers or winners & losers:
        raise ValueError('Resultado da Arena inválido.')
    db.execute('INSERT OR IGNORE INTO arena_seasons(season) VALUES(?)', (season,))
    winner_elo, loser_elo = arena_rules.event_ratings(db, queue, event_id, winners)
    win_delta, loss_delta = arena_rules.outcome_points(winner_elo, loser_elo)
    for pid in sorted(winners | losers):
        if db.execute('SELECT 1 FROM arena_results WHERE queue=? AND event_id=? AND player_id=?',
                      (queue,event_id,pid)).fetchone():
            continue
        closed = db.execute('SELECT closed_at FROM arena_seasons WHERE season=?',(season,)).fetchone()
        if closed['closed_at']:
            raise ValueError('Esta temporada já está encerrada.')
        db.execute('INSERT OR IGNORE INTO arena_standings(season,queue,player_id) VALUES(?,?,?)',(season,queue,pid))
        old = db.execute('SELECT * FROM arena_standings WHERE season=? AND queue=? AND player_id=?',(season,queue,pid)).fetchone()
        won = pid in winners
        delta = win_delta if won else loss_delta
        new = result_progress(old, won, delta)
        db.execute('''UPDATE arena_standings SET points=?,score_balance=?,emblem_points=?,wins=?,losses=?,loss_streak=?,loss_bank=?
          WHERE season=? AND queue=? AND player_id=?''',
          (new['points'],new['score_balance'],new['emblem_points'],new['wins'],new['losses'],
           new['loss_streak'],new['loss_bank'],season,queue,pid))
        db.execute('''INSERT INTO arena_results
          (queue,event_id,player_id,season,won,points_before,points_after,demoted,recorded_at,
           points_delta,rating_self,rating_opponent,rules_version,balance_before,balance_after,emblem_before,emblem_after)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
          (queue,event_id,pid,season,int(won),old['points'],new['points'],new['demoted'],str(when),delta,
           winner_elo if won else loser_elo,loser_elo if won else winner_elo,253,
           old['points'],new['score_balance'],old['emblem_points'],new['emblem_points']))


def init_v25_structure(db):
    """All schema changes run in the existing startup transaction."""
    for table in ('social_duels', 'arena_team_duels'):
        columns = {r['name'] for r in db.execute(f'PRAGMA table_info({table})')}
        for name, declaration in [('rating_a','REAL'),('rating_b','REAL'),('rating_source',"TEXT NOT NULL DEFAULT ''")]:
            if name not in columns:
                db.execute(f'ALTER TABLE {table} ADD COLUMN {name} {declaration}')
    columns = {r['name'] for r in db.execute('PRAGMA table_info(arena_standings)')}
    if 'score_balance' not in columns:
        # The score has no ceiling; ten badge tiers remain (Imortal starts at 900).
        db.execute('''CREATE TABLE arena_standings_v25 (
          season TEXT NOT NULL,queue TEXT NOT NULL CHECK(queue IN ('x1','2v2','3v3')),
          player_id INTEGER NOT NULL REFERENCES players(id),points INTEGER NOT NULL DEFAULT 0 CHECK(points>=0),
          wins INTEGER NOT NULL DEFAULT 0,losses INTEGER NOT NULL DEFAULT 0,
          loss_streak INTEGER NOT NULL DEFAULT 0,loss_bank INTEGER NOT NULL DEFAULT 0,
          score_balance INTEGER NOT NULL DEFAULT 0,emblem_points INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(season,queue,player_id))''')
        db.execute('INSERT INTO arena_standings_v25 SELECT *,points,points FROM arena_standings')
        db.execute('DROP TABLE arena_standings')
        db.execute('ALTER TABLE arena_standings_v25 RENAME TO arena_standings')
    columns = {r['name'] for r in db.execute('PRAGMA table_info(arena_results)')}
    for name, declaration in [('points_delta','INTEGER'),('rating_self','REAL'),('rating_opponent','REAL'),
                              ('rules_version','INTEGER NOT NULL DEFAULT 24'),('balance_before','INTEGER'),
                              ('balance_after','INTEGER'),('emblem_before','INTEGER'),('emblem_after','INTEGER')]:
        if name not in columns:
            db.execute(f'ALTER TABLE arena_results ADD COLUMN {name} {declaration}')
    db.execute('''CREATE TABLE IF NOT EXISTS arena_challenge_attempts (
      queue TEXT NOT NULL,event_id INTEGER NOT NULL,player_low INTEGER NOT NULL,player_high INTEGER NOT NULL,
      day TEXT NOT NULL,PRIMARY KEY(queue,event_id,player_low,player_high),CHECK(player_low<player_high))''')
    db.execute('CREATE INDEX IF NOT EXISTS idx_arena_attempt_pair_day ON arena_challenge_attempts(player_low,player_high,day)')


def migrate_v25(db):
    if db.execute("SELECT 1 FROM site_meta WHERE key='arena_v25_migrated'").fetchone():
        return
    # Save the previous score ledger, including archived months, before recomputing.
    for table in ('arena_standings','arena_results','arena_awards'):
        db.execute(f'CREATE TABLE IF NOT EXISTS {table}_before_v25 AS SELECT * FROM {table}')
    current = period()
    rows = db.execute('''SELECT queue,event_id,recorded_at FROM arena_results
      WHERE season=? GROUP BY queue,event_id ORDER BY julianday(recorded_at),event_id,queue''', (current,)).fetchall()
    events = []
    for row in rows:
        results = db.execute('SELECT player_id,won FROM arena_results WHERE queue=? AND event_id=?',
                             (row['queue'],row['event_id'])).fetchall()
        events.append((row, [r['player_id'] for r in results if r['won']], [r['player_id'] for r in results if not r['won']]))
    db.execute('DELETE FROM arena_results WHERE season=?', (current,))
    db.execute('DELETE FROM arena_standings WHERE season=?', (current,))
    for row, winners, losers in events:
        record_result(db,row['queue'],row['event_id'],winners,losers,row['recorded_at'])
    # Register existing challenges in the quota without guessing historical ratings.
    for row in db.execute('SELECT * FROM social_duels').fetchall():
        arena_rules.record_attempt(db,'x1',row['id'],[row['challenger_id']],[row['challenged_id']],row['requested_at'])
        if row['status'] in arena_rules.ACTIVE and not row['rating_source']:
            ratings = arena_rules.player_ratings(db,[row['challenger_id'],row['challenged_id']])
            db.execute("UPDATE social_duels SET rating_a=?,rating_b=?,rating_source='migration' WHERE id=?",
                       (ratings.get(row['challenger_id']),ratings.get(row['challenged_id']),row['id']))
    for row in db.execute('SELECT * FROM arena_team_duels').fetchall():
        members = db.execute('SELECT player_id,side FROM arena_duel_members WHERE duel_id=?',(row['id'],)).fetchall()
        a = [m['player_id'] for m in members if m['side']=='a']
        b = [m['player_id'] for m in members if m['side']=='b']
        queue = f"{row['size']}v{row['size']}"
        arena_rules.record_attempt(db,queue,row['id'],a,b,row['requested_at'])
        if row['status'] in arena_rules.ACTIVE and not row['rating_source']:
            ratings = arena_rules.player_ratings(db,a+b,queue)
            db.execute("UPDATE arena_team_duels SET rating_a=?,rating_b=?,rating_source='migration' WHERE id=?",
                       (arena_rules.average(ratings.get(p) for p in a),arena_rules.average(ratings.get(p) for p in b),row['id']))
    db.execute("INSERT INTO site_meta(key,value) VALUES('arena_v25_migrated',?)",(utc_now().isoformat(),))


def migrate_v25_1(db):
    """Replay the open month with a real zero floor; preserve match evidence."""
    if db.execute("SELECT 1 FROM site_meta WHERE key='arena_v25_1_migrated'").fetchone():
        return
    current = period()
    closed = db.execute('SELECT closed_at FROM arena_seasons WHERE season=?',(current,)).fetchone()
    if not closed or not closed['closed_at']:
        for table in ('arena_standings','arena_results'):
            db.execute(f'CREATE TABLE IF NOT EXISTS {table}_before_v25_1 AS SELECT * FROM {table}')
        rows = db.execute('''SELECT * FROM arena_results WHERE season=?
          ORDER BY julianday(recorded_at),rowid''',(current,)).fetchall()
        balances = {}
        for row in rows:
            key = (row['queue'],row['player_id'])
            before = balances.get(key,0)
            delta = row['points_delta'] if row['points_delta'] is not None else (30 if row['won'] else -20)
            after = max(0,before+delta)
            balances[key] = after
            db.execute('''UPDATE arena_results SET points_before=?,points_after=?,balance_before=?,balance_after=?,
              rules_version=251 WHERE queue=? AND event_id=? AND player_id=?''',
              (before,after,before,after,row['queue'],row['event_id'],row['player_id']))
        # Any standing without a ledger still loses its former hidden debt.
        db.execute('UPDATE arena_standings SET score_balance=MAX(0,points) WHERE season=?',(current,))
        for (queue,pid),points in balances.items():
            db.execute('''UPDATE arena_standings SET points=?,score_balance=?
              WHERE season=? AND queue=? AND player_id=?''',(points,points,current,queue,pid))
    db.execute("INSERT INTO site_meta(key,value) VALUES('arena_v25_1_migrated',?)",(utc_now().isoformat(),))


def migrate_v25_2(db):
    """Classify prior acceptance notices without changing any recorded score."""
    if db.execute("SELECT 1 FROM site_meta WHERE key='arena_v25_2_migrated'").fetchone():
        return
    db.execute('''UPDATE social_notifications AS n SET kind='team_accepted'
      WHERE n.kind='team' AND EXISTS (
        SELECT 1 FROM arena_teams t WHERE n.arena_url='/arena/equipe/' || t.id
          AND substr(n.message,-length(' aceitou o convite para ' || t.name || '.'))
            =' aceitou o convite para ' || t.name || '.')''')
    db.execute("INSERT INTO site_meta(key,value) VALUES('arena_v25_2_migrated',?)",(utc_now().isoformat(),))


def migrate_v25_3(db):
    """Apply the -30 base loss to the open month, keeping match evidence intact."""
    if db.execute("SELECT 1 FROM site_meta WHERE key='arena_v25_3_migrated'").fetchone():
        return
    current = period()
    season = db.execute('SELECT closed_at FROM arena_seasons WHERE season=?',(current,)).fetchone()
    if not season or not season['closed_at']:
        for table in ('arena_standings','arena_results'):
            db.execute(f'CREATE TABLE IF NOT EXISTS {table}_before_v25_3 AS SELECT * FROM {table} WHERE season=?',(current,))
        rows = db.execute('''SELECT * FROM arena_results WHERE season=?
          ORDER BY julianday(recorded_at),rowid''',(current,)).fetchall()
        states = {}
        empty = dict(points=0,emblem_points=0,wins=0,losses=0,loss_streak=0,loss_bank=0)
        for row in rows:
            key = (row['queue'],row['player_id'])
            old = states.get(key,empty)
            delta = row['points_delta']
            if delta is None:
                # Use historical ratings only; today's profile cannot change an old bonus.
                ratings = (row['rating_self'],row['rating_opponent']) if row['won'] else (
                    row['rating_opponent'],row['rating_self'])
                delta = arena_rules.outcome_points(*ratings)[0 if row['won'] else 1]
            elif not row['won'] and delta in (-15,-20):
                delta = -30
            new = result_progress(old, bool(row['won']), delta)
            db.execute('''UPDATE arena_results SET points_delta=?,points_before=?,points_after=?,
              balance_before=?,balance_after=?,emblem_before=?,emblem_after=?,demoted=?,rules_version=253
              WHERE queue=? AND event_id=? AND player_id=?''',
              (delta,old['points'],new['points'],old['points'],new['score_balance'],
               old['emblem_points'],new['emblem_points'],new['demoted'],row['queue'],row['event_id'],row['player_id']))
            states[key] = new
        for (queue,pid),state in states.items():
            db.execute('''INSERT INTO arena_standings
              (season,queue,player_id,points,score_balance,emblem_points,wins,losses,loss_streak,loss_bank)
              VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(season,queue,player_id) DO UPDATE SET
              points=excluded.points,score_balance=excluded.score_balance,emblem_points=excluded.emblem_points,
              wins=excluded.wins,losses=excluded.losses,loss_streak=excluded.loss_streak,loss_bank=excluded.loss_bank''',
              (current,queue,pid,state['points'],state['score_balance'],state['emblem_points'],
               state['wins'],state['losses'],state['loss_streak'],state['loss_bank']))
    db.execute("INSERT INTO site_meta(key,value) VALUES('arena_v25_3_migrated',?)",(utc_now().isoformat(),))


def init_arena(db):
    db.executescript((Path(__file__).parent/'arena_schema.sql').read_text())
    db.execute('BEGIN IMMEDIATE')
    init_v25_structure(db)
    columns = {r['name'] for r in db.execute('PRAGMA table_info(social_notifications)')}
    if 'arena_url' not in columns:
        db.execute("ALTER TABLE social_notifications ADD COLUMN arena_url TEXT NOT NULL DEFAULT ''")
    # Import verified results once, in confirmation order. Original duels stay intact.
    if not db.execute("SELECT 1 FROM site_meta WHERE key='arena_v24_imported'").fetchone():
        rows = db.execute("""SELECT * FROM social_duels WHERE status='completed' AND winner_id IS NOT NULL
          AND loser_id IS NOT NULL AND match_id<>'' AND finished_at<>'' ORDER BY finished_at,id""").fetchall()
        for row in rows:
            try:
                verified = json.loads(row['match_payload'] or '{}').get('state')=='completed'
                if verified: record_result(db,'x1',row['id'],[row['winner_id']],[row['loser_id']],row['finished_at'])
            except (ValueError,TypeError):
                continue
        db.execute("INSERT INTO site_meta(key,value) VALUES('arena_v24_imported','1')")
    migrate_v25(db)
    migrate_v25_1(db)
    migrate_v25_2(db)
    migrate_v25_3(db)
    close_seasons(db)

def standings(db, queue='x1', season=None):
    season = season or period()
    close_seasons(db)
    # A completed month is archived on first access; no scheduled server required.
    db.commit()
    return {r['player_id']:dict(r, badge=standing_badge(r)) for r in db.execute(
        'SELECT * FROM arena_standings WHERE season=? AND queue=?',(season,queue))}

def profile_seasons(db, player_id):
    close_seasons(db)
    db.commit()
    current = [dict(r, badge=standing_badge(r),label=QUEUES[r['queue']]) for r in db.execute(
        'SELECT * FROM arena_standings WHERE season=? AND player_id=? ORDER BY queue',(period(),player_id))]
    awards = [dict(r, badge=badge((r['tier']-1)*100),label=QUEUES[r['queue']]) for r in db.execute(
        'SELECT * FROM arena_awards WHERE player_id=? ORDER BY season DESC,queue LIMIT 36',(player_id,))]
    return dict(current=current,awards=awards,season=period())
