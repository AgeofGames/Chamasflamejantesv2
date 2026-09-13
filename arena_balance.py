"""V28: monthly ranked evidence and transactional, repeatable Arena repairs."""
from datetime import datetime, timezone
import json
import os
import sqlite3
import threading
import time

import arena_rules
from aomstats_activity import fetch_activity

VERSION = 280
MIN_RANKED = 8


def month(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(arena_rules.ZONE).strftime('%Y-%m')


def init_schema(db):
    columns = {r['name'] for r in db.execute('PRAGMA table_info(arena_results)')}
    for name, decl in [('benefit_applied', 'INTEGER NOT NULL DEFAULT 0'),
                       ('ranked_games_month', 'INTEGER'), ('benefit_month', 'TEXT')]:
        if name not in columns:
            db.execute(f'ALTER TABLE arena_results ADD COLUMN {name} {decl}')
    statements = [
        '''CREATE TABLE IF NOT EXISTS arena_ranked_activity (
            profile_id TEXT NOT NULL,match_id TEXT NOT NULL,leaderboard_id INTEGER NOT NULL CHECK(leaderboard_id BETWEEN 1 AND 4),
            completed_at TEXT NOT NULL,month TEXT NOT NULL,source_url TEXT NOT NULL,checked_at TEXT NOT NULL,
            PRIMARY KEY(profile_id,match_id))''',
        'CREATE INDEX IF NOT EXISTS idx_arena_activity_month ON arena_ranked_activity(profile_id,month)',
        '''CREATE TABLE IF NOT EXISTS arena_activity_jobs (
            profile_id TEXT PRIMARY KEY,checked_at REAL NOT NULL DEFAULT 0,
            lease_until REAL NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'pending')''',
        '''CREATE TABLE IF NOT EXISTS arena_balance_reviews (
            queue TEXT NOT NULL,event_id INTEGER NOT NULL,season TEXT NOT NULL,
            profile_ids TEXT NOT NULL DEFAULT '[]',status TEXT NOT NULL DEFAULT 'pending',
            checked_at TEXT NOT NULL DEFAULT '',PRIMARY KEY(queue,event_id))''',
        '''CREATE TABLE IF NOT EXISTS arena_balance_adjustments (
            queue TEXT NOT NULL,event_id INTEGER NOT NULL,player_id INTEGER NOT NULL,
            original_result TEXT NOT NULL,new_delta INTEGER NOT NULL,evidence TEXT NOT NULL,
            adjusted_at TEXT NOT NULL,PRIMARY KEY(queue,event_id,player_id))''',
    ]
    for sql in statements:
        db.execute(sql)
    if not db.execute("SELECT 1 FROM site_meta WHERE key='arena_v28_prepared'").fetchone():
        for table in ('arena_results', 'arena_standings', 'arena_awards'):
            db.execute(f'CREATE TABLE IF NOT EXISTS {table}_before_v28 AS SELECT * FROM {table}')
        for row in db.execute('''SELECT DISTINCT queue,event_id FROM arena_results
                WHERE won=1 AND rating_self>0 AND rating_self<1000 AND rating_opponent>=1000''').fetchall():
            queue_review(db, row['queue'], row['event_id'])
        db.execute("INSERT INTO site_meta(key,value) VALUES('arena_v28_prepared',?)", (datetime.now(timezone.utc).isoformat(),))


def winner_profiles(db, queue, event_id, winner_ids):
    """Use verified match identity or the immutable team roster, never today's profile."""
    if queue == 'x1':
        row = db.execute('SELECT winner_id,match_payload FROM social_duels WHERE id=?', (event_id,)).fetchone()
        if not row or row['winner_id'] not in winner_ids:
            return []
        try:
            payload = json.loads(row['match_payload'] or '{}')
            profile = str(payload.get('winner_profile_id', ''))
            if payload.get('state') == 'completed' and profile.isdigit():
                return [profile]
        except (ValueError, TypeError, AttributeError):
            pass
        return []
    rows = db.execute('SELECT player_id,profile_id FROM arena_duel_members WHERE duel_id=?', (event_id,)).fetchall()
    profiles = [str(r['profile_id']) for r in rows if r['player_id'] in winner_ids]
    if len(profiles) != len(winner_ids) or len(set(profiles)) != len(profiles) or not all(p.isdigit() for p in profiles):
        return []
    return sorted(profiles)


def activity_count(db, profile_id, season):
    return db.execute('SELECT COUNT(*) FROM arena_ranked_activity WHERE profile_id=? AND month=?',
                      (str(profile_id), season)).fetchone()[0]


def benefit_context(db, queue, event_id, winners, winner_rating, loser_rating, season):
    winner_rating, loser_rating = arena_rules.rating(winner_rating), arena_rules.rating(loser_rating)
    candidate = winner_rating is not None and loser_rating is not None and winner_rating < 1000 <= loser_rating
    profiles = winner_profiles(db, queue, event_id, set(winners)) if candidate else []
    count = min((activity_count(db, p, season) for p in profiles), default=0)
    return dict(candidate=candidate, profiles=profiles, count=count, eligible=bool(profiles) and count >= MIN_RANKED)


def queue_review(db, queue, event_id):
    rows = db.execute('SELECT * FROM arena_results WHERE queue=? AND event_id=?', (queue, event_id)).fetchall()
    winners = [r for r in rows if r['won']]
    if not winners:
        return
    row = winners[0]
    context = benefit_context(db, queue, event_id, [r['player_id'] for r in winners],
                              row['rating_self'], row['rating_opponent'], row['season'])
    if not context['candidate']:
        return
    status = 'applied' if all(r['benefit_applied'] for r in rows) else 'pending' if context['profiles'] else 'missing_profile'
    db.execute('''INSERT INTO arena_balance_reviews(queue,event_id,season,profile_ids,status) VALUES(?,?,?,?,?)
        ON CONFLICT(queue,event_id) DO NOTHING''',
        (queue, event_id, row['season'], json.dumps(context['profiles']), status))
    for profile in context['profiles']:
        db.execute('INSERT OR IGNORE INTO arena_activity_jobs(profile_id) VALUES(?)', (profile,))


def store_activity(db, profile_id, evidence):
    """Called with evidence fetched by our server, never request-form counters."""
    stamp = datetime.now(timezone.utc).isoformat()
    for item in evidence.get('records', []):
        if str(item['profile_id']) != str(profile_id):
            continue
        db.execute('''INSERT OR IGNORE INTO arena_ranked_activity
            (profile_id,match_id,leaderboard_id,completed_at,month,source_url,checked_at) VALUES(?,?,?,?,?,?,?)''',
            (str(profile_id), item['match_id'], item['leaderboard_id'], item['completed_at'],
             month(item['completed_at']), item['source_url'], stamp))
    db.execute('''INSERT INTO arena_activity_jobs(profile_id,checked_at,status) VALUES(?,?,?)
        ON CONFLICT(profile_id) DO UPDATE SET checked_at=excluded.checked_at,lease_until=0,status=excluded.status''',
        (str(profile_id), time.time(), 'checked' if evidence.get('available') else 'unavailable'))


def prepare_activity(db, profiles, season):
    """Network happens before the match transaction. Results remain retryable."""
    evidence = {}
    for profile in sorted(set(profiles)):
        if activity_count(db, profile, season) >= MIN_RANKED:
            continue
        job = db.execute('SELECT * FROM arena_activity_jobs WHERE profile_id=?', (profile,)).fetchone()
        if job and (job['checked_at'] > time.time() - 300 or job['lease_until'] > time.time()):
            continue
        evidence[profile] = fetch_activity(profile)
    return evidence


def rebuild_ladder(db, season, queue):
    """Replay only affected ladders, preserving each result's original order/identity."""
    from arena_seasons import result_progress
    rows = db.execute('''SELECT * FROM arena_results WHERE season=? AND queue=?
        ORDER BY julianday(recorded_at),rowid''', (season, queue)).fetchall()
    states = {}
    empty = dict(points=0, emblem_points=0, wins=0, losses=0, loss_streak=0, loss_bank=0)
    for row in rows:
        old = states.get(row['player_id'], empty)
        delta = row['points_delta']
        if delta is None:
            # Legacy rows have no nominal delta. Preserve their recorded change.
            delta = row['points_after'] - row['points_before']
        new = result_progress(old, bool(row['won']), delta)
        db.execute('''UPDATE arena_results SET points_before=?,points_after=?,balance_before=?,balance_after=?,
            emblem_before=?,emblem_after=?,demoted=? WHERE queue=? AND event_id=? AND player_id=?''',
            (old['points'], new['points'], old['points'], new['points'], old['emblem_points'],
             new['emblem_points'], new['demoted'], queue, row['event_id'], row['player_id']))
        states[row['player_id']] = new
    for pid, new in states.items():
        db.execute('''INSERT INTO arena_standings
            (season,queue,player_id,points,score_balance,emblem_points,wins,losses,loss_streak,loss_bank)
            VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(season,queue,player_id) DO UPDATE SET
            points=excluded.points,score_balance=excluded.score_balance,emblem_points=excluded.emblem_points,
            wins=excluded.wins,losses=excluded.losses,loss_streak=excluded.loss_streak,loss_bank=excluded.loss_bank''',
            (season, queue, pid, new['points'], new['points'], new['emblem_points'], new['wins'],
             new['losses'], new['loss_streak'], new['loss_bank']))
    closed = db.execute('SELECT closed_at FROM arena_seasons WHERE season=?', (season,)).fetchone()
    if closed and closed['closed_at']:
        db.execute('DELETE FROM arena_awards WHERE season=? AND queue=?', (season, queue))
        db.execute('''INSERT INTO arena_awards
            SELECT season,queue,player_id,MIN(9,emblem_points/100)+1,points,
                ROW_NUMBER() OVER(ORDER BY points DESC,wins DESC,losses,player_id),wins,losses
            FROM arena_standings WHERE season=? AND queue=? AND wins+losses>0''', (season, queue))


def reconcile(db):
    """Caller owns one transaction covering audit, both opponents and all balances."""
    changed, affected = 0, set()
    for review in db.execute("SELECT * FROM arena_balance_reviews WHERE status='pending'").fetchall():
        rows = db.execute('SELECT * FROM arena_results WHERE queue=? AND event_id=?',
                          (review['queue'], review['event_id'])).fetchall()
        winners = [r for r in rows if r['won']]
        losers = [r for r in rows if not r['won']]
        if not winners or not losers:
            continue
        row = winners[0]
        size = {'x1': 1, '2v2': 2, '3v3': 3}.get(review['queue'])
        if (len(winners) != size or len(losers) != size
                or not (0 < (row['rating_self'] or 0) < 1000 <= (row['rating_opponent'] or 0))
                or any((r['rating_self'], r['rating_opponent']) != (row['rating_self'], row['rating_opponent']) for r in winners)
                or any((r['rating_opponent'], r['rating_self']) != (row['rating_self'], row['rating_opponent']) for r in losers)):
            continue
        profiles = json.loads(review['profile_ids'])
        if len(profiles) != size or len(set(profiles)) != size:
            continue
        counts = {p: activity_count(db, p, review['season']) for p in profiles}
        if not counts or min(counts.values()) < MIN_RANKED:
            continue
        # Incomplete or inconsistent result groups must not receive half a repair.
        if any(r['season'] != review['season'] or r['points_delta'] is None for r in rows):
            continue
        win_delta, loss_delta = arena_rules.outcome_points(row['rating_self'], row['rating_opponent'], min(counts.values()))
        evidence = {p: [dict(r) for r in db.execute('''SELECT match_id,leaderboard_id,completed_at,source_url
                    FROM arena_ranked_activity WHERE profile_id=? AND month=? ORDER BY completed_at,match_id''',
                    (p, review['season']))] for p in profiles}
        stamp = datetime.now(timezone.utc).isoformat()
        for entry in rows:
            delta = win_delta if entry['won'] else loss_delta
            db.execute('''INSERT OR IGNORE INTO arena_balance_adjustments VALUES(?,?,?,?,?,?,?)''',
                (entry['queue'], entry['event_id'], entry['player_id'], json.dumps(dict(entry)),
                 delta, json.dumps(evidence), stamp))
            db.execute('''UPDATE arena_results SET points_delta=?,rules_version=?,benefit_applied=1,
                ranked_games_month=?,benefit_month=? WHERE queue=? AND event_id=? AND player_id=?''',
                (delta, VERSION, min(counts.values()), review['season'], entry['queue'], entry['event_id'], entry['player_id']))
        db.execute("UPDATE arena_balance_reviews SET status='applied',checked_at=? WHERE queue=? AND event_id=?",
                   (stamp, review['queue'], review['event_id']))
        affected.add((review['season'], review['queue']))
        changed += 1
    for season, queue in sorted(affected):
        rebuild_ladder(db, season, queue)
    return changed


def process_one(db):
    """A durable lease shares work across Railway workers; no network under a lock."""
    now = time.time()
    db.execute('BEGIN IMMEDIATE')
    try:
        reconcile(db)
        job = db.execute('''SELECT j.* FROM arena_activity_jobs j WHERE j.lease_until<? AND j.checked_at<?
            AND EXISTS(SELECT 1 FROM arena_balance_reviews r,json_each(r.profile_ids) p
                WHERE r.status='pending' AND p.value=j.profile_id)
            ORDER BY j.checked_at,j.profile_id LIMIT 1''', (now, now - 900)).fetchone()
        if job:
            db.execute('UPDATE arena_activity_jobs SET lease_until=? WHERE profile_id=?', (now + 120, job['profile_id']))
        db.commit()
    except Exception:
        db.rollback()
        raise
    if not job:
        return False
    evidence = fetch_activity(job['profile_id'])
    db.execute('BEGIN IMMEDIATE')
    try:
        store_activity(db, job['profile_id'], evidence)
        reconcile(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def install(app, api):
    from flask import render_template, request, redirect, url_for, flash

    @app.route('/admin/arena-pontos', methods=['GET', 'POST'])
    @api['admin_required']
    def admin_arena_points():
        db = api['get_db']()
        if request.method == 'POST':
            api['require_csrf']()
            db.execute('BEGIN IMMEDIATE')
            db.execute('UPDATE arena_activity_jobs SET checked_at=0')
            reconcile(db)
            db.commit()
            flash('Verificação solicitada. As partidas serão revisadas conforme o AoMStats confirmar a atividade mensal.', 'success')
            return redirect(url_for('admin_arena_points'))
        reviews = [dict(r) for r in db.execute('''SELECT r.*,
                CASE WHEN r.queue='x1' THEN d.match_id ELSE t.match_id END match_id
            FROM arena_balance_reviews r LEFT JOIN social_duels d ON r.queue='x1' AND d.id=r.event_id
            LEFT JOIN arena_team_duels t ON r.queue<>'x1' AND t.id=r.event_id
            ORDER BY r.season DESC,r.event_id DESC LIMIT 100''')]
        for row in reviews:
            row['counts'] = [(p, activity_count(db, p, row['season'])) for p in json.loads(row['profile_ids'])]
        totals = dict(db.execute('SELECT status,COUNT(*) FROM arena_balance_reviews GROUP BY status').fetchall())
        return render_template('admin_arena_points.html', reviews=reviews, totals=totals)


def start_worker(app, api):
    if os.environ.get('ARENA_ACTIVITY_ENABLED', '1').lower() in ('0', 'false', 'no'):
        return
    stop = threading.Event()

    def worker():
        while not stop.wait(30):
            if app.config.get('TESTING'):
                continue
            try:
                with app.app_context():
                    process_one(api['get_db']())
            except (sqlite3.Error, ValueError, TypeError):
                app.logger.warning('Atividade mensal da Arena: verificação adiada; nova tentativa automática.')
    app.extensions['arena_activity_stop'] = stop
    threading.Thread(target=worker, name='arena-ranked-activity', daemon=True).start()
