"""Transactional ranking ledger. Season boundaries use the Brasília calendar."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json

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

def close_seasons(db, current=None):
    current = current or period()
    for row in db.execute("SELECT season FROM arena_seasons WHERE season<? AND closed_at=''", (current,)).fetchall():
        db.execute('''INSERT OR IGNORE INTO arena_awards
          SELECT season,queue,player_id,MIN(9,points/100)+1,points,
            ROW_NUMBER() OVER(PARTITION BY queue ORDER BY points DESC,wins DESC,losses,player_id),wins,losses
          FROM arena_standings WHERE season=? AND wins+losses>0''', (row['season'],))
        db.execute("UPDATE arena_seasons SET closed_at=CURRENT_TIMESTAMP WHERE season=?", (row['season'],))

def record_result(db, queue, event_id, winners, losers, when=None):
    """Caller owns the transaction: the match and all its points commit together."""
    when = when or utc_now().isoformat()
    season = period(when)
    winners, losers = set(winners), set(losers)
    if queue not in QUEUES or not winners or not losers or winners & losers:
        raise ValueError('Resultado da Arena inválido.')
    db.execute('INSERT OR IGNORE INTO arena_seasons(season) VALUES(?)', (season,))
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
        points = min(999,old['points']+30) if won else max(0,old['points']-15)
        streak = 0 if won else old['loss_streak']+1
        bank = old['loss_bank'] if won else old['loss_bank']+1
        forced = not won and (streak>=3 or bank>=4)
        if forced:
            # A natural points demotion on this loss already satisfies the penalty.
            points = min(points,max(0,(old['points']//100)*100-1))
            streak = bank = 0
        demoted = points//100 < old['points']//100
        db.execute('''UPDATE arena_standings SET points=?,wins=wins+?,losses=losses+?,loss_streak=?,loss_bank=?
          WHERE season=? AND queue=? AND player_id=?''', (points,int(won),int(not won),streak,bank,season,queue,pid))
        db.execute('INSERT INTO arena_results VALUES(?,?,?,?,?,?,?,?,?)',
                   (queue,event_id,pid,season,int(won),old['points'],points,int(demoted),str(when)))

def init_arena(db):
    db.executescript((Path(__file__).parent/'arena_schema.sql').read_text())
    db.execute('BEGIN IMMEDIATE')
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
    close_seasons(db)

def standings(db, queue='x1', season=None):
    season = season or period()
    close_seasons(db)
    # A completed month is archived on first access; no scheduled server required.
    db.commit()
    return {r['player_id']:dict(r, badge=badge(r['points'])) for r in db.execute(
        'SELECT * FROM arena_standings WHERE season=? AND queue=?',(season,queue))}

def profile_seasons(db, player_id):
    close_seasons(db)
    db.commit()
    current = [dict(r, badge=badge(r['points']),label=QUEUES[r['queue']]) for r in db.execute(
        'SELECT * FROM arena_standings WHERE season=? AND player_id=? ORDER BY queue',(period(),player_id))]
    awards = [dict(r, badge=badge((r['tier']-1)*100),label=QUEUES[r['queue']]) for r in db.execute(
        'SELECT * FROM arena_awards WHERE player_id=? ORDER BY season DESC,queue LIMIT 36',(player_id,))]
    return dict(current=current,awards=awards,season=period())
