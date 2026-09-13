"""Current public AoMStats activity, shared across Railway/Gunicorn workers.

Read only the three public lobby lists. Never infer presence from a nickname,
profile history, a challenge on this site, or a Google session.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import json
import time
import uuid

from bs4 import BeautifulSoup
import requests

from aomstats_matches import _tokens, _serialized_records

SOURCES = {'ranked': 'https://aomstats.io/lobbies',
           'customs': 'https://aomstats.io/lobbies/customs',
           'open': 'https://aomstats.io/lobbies/open'}
REFRESH_SECONDS = 45
PRESENCE_TTL = 90
SOURCE_MAX_AGE = 180
FETCH_BUDGET = 12
MAX_BYTES = 4 * 1024 * 1024
_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='aom-presence')


def init_cache(db):
    db.execute('''CREATE TABLE IF NOT EXISTS aom_presence_cache (
        source TEXT PRIMARY KEY, payload TEXT NOT NULL DEFAULT '{}',
        source_at REAL NOT NULL DEFAULT 0, expires_at REAL NOT NULL DEFAULT 0,
        next_attempt REAL NOT NULL DEFAULT 0, lease_until REAL NOT NULL DEFAULT 0,
        lease_token TEXT NOT NULL DEFAULT '')''')
    db.executemany('INSERT OR IGNORE INTO aom_presence_cache(source) VALUES(?)',
                   [(key,) for key in SOURCES])


def _lobby_literals(script):
    """Isolate actual lobbies arrays, not similarly named text inside aliases."""
    tokens = list(_tokens.finditer(script))
    arrays, timestamps = [], []
    for i in range(1, len(tokens) - 2):
        key = tokens[i].group()
        if tokens[i-1].group() not in ('{', ',') or tokens[i+1].group() != ':':
            continue
        value = tokens[i+2]
        if key in ('lastLobbyTime', '"lastLobbyTime"') and value.group().isdigit():
            timestamps.append(int(value.group()))
        if key not in ('lobbies', '"lobbies"') or value.group() != '[':
            continue
        depth = 1
        for end in tokens[i+3:]:
            if end.group() == '[': depth += 1
            elif end.group() == ']': depth -= 1
            if depth == 0:
                arrays.append(script[value.start():end.end()])
                break
        else:
            raise ValueError('Incomplete lobby list')
    return arrays, timestamps


def parse_lobbies(document, source, now=None):
    now = time.time() if now is None else now
    arrays, timestamps = [], []
    for script in BeautifulSoup(document, 'html.parser').find_all('script'):
        found, times = _lobby_literals(script.get_text())
        arrays.extend(found); timestamps.extend(times)
    if not arrays or not timestamps:
        raise ValueError('AoMStats lobby structure not recognized')
    source_at = min(timestamps)
    if not now - SOURCE_MAX_AGE < source_at <= now + 60:
        raise ValueError('AoMStats lobby snapshot is stale')
    players = {}
    for literal in arrays:
        for row in _serialized_records(literal):
            # Positive raw IDs also identify humans who have no ranked profile.
            raw, profile = row.get('raw_profile_id'), row.get('profile_id')
            if type(raw) is not int or raw <= 0: continue
            if profile is not None and profile != raw: continue
            if type(row.get('match_id')) is not int or row['match_id'] <= 0: continue
            if any(key in row for key in ('win', 'resulttype', 'completiontime', 'endgametime')):
                continue
            start = row.get('startgametime')
            if type(start) is not int: continue
            if source == 'open' and row.get('joinable') is True and start <= 0:
                players[str(raw)] = 'lobby'
            elif source in ('ranked', 'customs') and row.get('joinable') is False and 0 < start <= source_at + 60:
                players[str(raw)] = 'match'
    return {'players': players, 'source_at': source_at}


def fetch_source(source):
    deadline = time.monotonic() + FETCH_BUDGET
    with requests.get(SOURCES[source], headers={
        'User-Agent': 'ChamasFlamejantes/25.4 (+https://chamasflamejantes.com.br)',
        'Accept': 'text/html', 'Accept-Language': 'en-US,en;q=0.9',
    }, timeout=(5, 5), stream=True, allow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError('AoMStats lobbies unavailable')
        chunks, size = [], 0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > MAX_BYTES or time.monotonic() >= deadline:
                raise ValueError('AoMStats lobby fetch exceeded its budget')
            chunks.append(chunk)
    return parse_lobbies(b''.join(chunks).decode('utf-8', errors='replace'), source)


def snapshot(db):
    """One refresh per source/45 s across workers. No lock during HTTP work."""
    now, token = time.time(), uuid.uuid4().hex
    claimed = []
    due = [row['source'] for row in db.execute('''SELECT source FROM aom_presence_cache
        WHERE next_attempt<=? AND lease_until<=?''', (now, now)).fetchall()]
    for source in due:
        updated = db.execute('''UPDATE aom_presence_cache SET lease_until=?,
            lease_token=?, next_attempt=? WHERE source=? AND lease_until<=?
            AND next_attempt<=?''',
            (now+20, token, now+REFRESH_SECONDS, source, now, now)).rowcount
        if updated: claimed.append(source)
    if due: db.commit()
    jobs = {_pool.submit(fetch_source, source): source for source in claimed}
    results = {}
    try:
        for job in as_completed(jobs, timeout=FETCH_BUDGET + 1):
            try: results[jobs[job]] = job.result()
            except (requests.RequestException, ValueError, TypeError): pass
    except TimeoutError:
        pass
    finally:
        for job in jobs: job.cancel()
    now = time.time()
    for source in claimed:
        result = results.get(source)
        if result:
            expires = min(now + PRESENCE_TTL, result['source_at'] + SOURCE_MAX_AGE)
            db.execute('''UPDATE aom_presence_cache SET payload=?, source_at=?,
                expires_at=?, lease_until=0, lease_token='' WHERE source=? AND lease_token=?''',
                (json.dumps(result['players']), result['source_at'], expires, source, token))
        else:
            # A failure never extends a previous confirmation's lifetime.
            db.execute("UPDATE aom_presence_cache SET lease_until=0, lease_token='' WHERE source=? AND lease_token=?",
                       (source, token))
    if claimed: db.commit()
    active = {}
    for row in db.execute('SELECT * FROM aom_presence_cache WHERE expires_at>?', (now,)):
        for profile, state in json.loads(row['payload']).items():
            current = active.get(profile)
            candidate = {'state': state, 'source_at': row['source_at'], 'expires_at': row['expires_at']}
            # A more recent room takes precedence over an older match listing.
            if not current or (candidate['source_at'], state == 'match') > (current['source_at'], current['state'] == 'match'):
                active[profile] = candidate
    return active


def install_presence(app, get_db):
    from flask import jsonify

    @app.get('/api/arena/presenca')
    def arena_presence():
        db = get_db()
        active, now = snapshot(db), time.time()
        players = {}
        for row in db.execute('SELECT id,aomstats_profile_id FROM players WHERE is_active=1'):
            item = active.get(str(row['aomstats_profile_id']))
            if item and item['expires_at'] > now:
                players[str(row['id'])] = {'state': item['state'],
                    'expires_in': max(0, int(item['expires_at'] - now))}
        return jsonify(players=players, refresh_after=20, source=SOURCES['ranked'])
