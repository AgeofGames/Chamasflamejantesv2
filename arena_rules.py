"""Arena rules shared by X1, teams and the transactional challenge quota."""
from datetime import datetime, timezone
from itertools import product
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('America/Sao_Paulo')
DAILY_LIMIT = 3
ACTIVE = ('pending', 'accepted', 'match_pending')


def local_day(value=None):
    value = value or datetime.now(timezone.utc)
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(ZONE).date().isoformat()


def rating(value):
    return float(value) if value is not None and 0 < float(value) <= 5000 else None


def outcome_points(winner_rating=None, loser_rating=None):
    """At exactly 100 use base points; 101..199 = 90; 200..299 = 120."""
    winner_rating, loser_rating = rating(winner_rating), rating(loser_rating)
    if winner_rating is not None and loser_rating is not None:
        gap = loser_rating - winner_rating
        if gap > 100:
            bonus = 90 + 30 * max(0, int(gap // 100) - 1)
            return bonus, -bonus
    return 30, -30


def most_challenged(db, when=None):
    """Incoming X1 challenges this Brasília month; all tied leaders share the tag."""
    now = when or datetime.now(timezone.utc)
    if isinstance(now, str):
        now = datetime.fromisoformat(now.replace('Z', '+00:00'))
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    start = now.astimezone(ZONE).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = start.replace(year=start.year+1, month=1) if start.month == 12 else start.replace(month=start.month+1)
    rows = db.execute('''SELECT d.challenged_id, COUNT(*) received
      FROM social_duels d JOIN players p ON p.id=d.challenged_id
      WHERE julianday(d.requested_at)>=julianday(?) AND julianday(d.requested_at)<julianday(?)
        AND d.status IN ('pending','accepted','match_pending','completed','refused')
        AND d.challenger_id<>d.challenged_id AND p.is_active=1
        AND COALESCE(p.aomstats_profile_id,'')<>'' AND COALESCE(p.aomstats_url,'')<>''
      GROUP BY d.challenged_id''', (start.isoformat(), end.isoformat())).fetchall()
    maximum = max((r['received'] for r in rows), default=0)
    return {r['challenged_id']: r['received'] for r in rows if r['received'] == maximum}


def player_ratings(db, ids, queue='x1'):
    ids = sorted(set(ids))
    column = 'elo_1v1' if queue == 'x1' else 'elo_team'
    rows = db.execute(f"SELECT id,{column} elo FROM players WHERE id IN ({','.join('?' for _ in ids)})", ids)
    return {r['id']: rating(r['elo']) for r in rows}


def average(values):
    values = list(values)
    return sum(values) / len(values) if values and all(v is not None for v in values) else None


def pairs(a, b):
    return sorted({tuple(sorted((x, y))) for x, y in product(a, b) if x != y})


def challenge_check(db, a, b, queue='x1', when=None):
    """Read under the caller's write lock before creating a challenge."""
    a, b = set(a), set(b)
    ratings = player_ratings(db, a | b, queue)
    counts = []
    for low, high in pairs(a, b):
        count = db.execute('''SELECT COUNT(*) FROM arena_challenge_attempts
            WHERE player_low=? AND player_high=? AND day=?''', (low, high, local_day(when))).fetchone()[0]
        counts.append(count)
    remaining = max(0, DAILY_LIMIT - max(counts, default=0))
    reason = ''
    for x, y in product(a, b):
        rx, ry = ratings.get(x), ratings.get(y)
        if max(rx or 0, ry or 0) >= 1300:
            if rx is None or ry is None:
                reason = 'Para enfrentar Elo 1300 ou mais, todos os adversários precisam ter Elo conhecido acima de 1000.'
            elif min(rx, ry) <= 1000:
                reason = 'Elo 1300 ou mais não enfrenta Elo 1000 ou menos. O jogador de Elo menor precisa passar de 1000.'
    if not remaining:
        reason = 'Limite de 3 desafios por dia entre os mesmos adversários atingido. Tente após a meia-noite de Brasília.'
    return dict(allowed=not reason, reason=reason, remaining=remaining,
                rating_a=average(ratings.get(pid) for pid in a),
                rating_b=average(ratings.get(pid) for pid in b))


def record_attempt(db, queue, event_id, a, b, when=None):
    # No duel foreign key: cancellation must not restore the daily allowance.
    db.executemany('''INSERT OR IGNORE INTO arena_challenge_attempts
        (queue,event_id,player_low,player_high,day) VALUES(?,?,?,?,?)''',
        [(queue, event_id, lo, hi, local_day(when)) for lo, hi in pairs(a, b)])


def event_ratings(db, queue, event_id, winners):
    if queue == 'x1':
        row = db.execute('SELECT * FROM social_duels WHERE id=?', (event_id,)).fetchone()
        winner_a = row and row['challenger_id'] in winners
    else:
        row = db.execute('SELECT * FROM arena_team_duels WHERE id=?', (event_id,)).fetchone()
        winner_a = row and row['winner_side'] == 'a'
    if row and row['rating_source']:
        return (row['rating_a'], row['rating_b']) if winner_a else (row['rating_b'], row['rating_a'])
    return None, None
