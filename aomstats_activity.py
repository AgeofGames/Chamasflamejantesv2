"""Positive evidence of ranked activity, read from public AoMStats pages.

Only dated, completed ranked match records count. Lifetime profile totals,
Customs/Quickplay, inferred results and missing pages never prove eligibility.
Schema reference: https://aomstats.io/api (leaderboards 1 through 4).
"""
from concurrent.futures import as_completed, TimeoutError
from datetime import datetime, timezone
import time

from bs4 import BeautifulSoup
from aomstats_matches import _serialized_records, _fetch_document, _pool, _slots


def parse_activity(document, profile_id, now=None):
    now = now or datetime.now(timezone.utc)
    latest = int(now.timestamp())
    found = {}
    conflicts = set()
    for script in BeautifulSoup(document, 'html.parser').find_all('script'):
        for row in _serialized_records(script.get_text()):
            if str(row.get('profile_id')) != str(profile_id):
                continue
            mid, board = row.get('match_id'), row.get('leaderboard_id')
            ended, started = row.get('completiontime'), row.get('startgametime')
            result = row.get('resulttype')
            if (type(mid) is not int or mid <= 0 or type(board) is not int or board not in (1, 2, 3, 4)
                    or type(ended) is not int or not 1700000000 <= ended <= latest
                    or type(started) is not int or not 1700000000 <= started < ended
                    or type(result) is not int or result not in (0, 1)
                    or row.get('missing_from_api') is True
                    or row.get('out_of_sync') is True):
                continue
            if type(row.get('win')) is bool and row['win'] != bool(result):
                continue
            item = dict(match_id=str(mid), profile_id=str(profile_id), leaderboard_id=board,
                        completed_at=datetime.fromtimestamp(ended, timezone.utc).isoformat())
            if mid in found and found[mid] != item:
                conflicts.add(mid)
            found[mid] = item
    return [item for mid, item in found.items() if mid not in conflicts]


def fetch_activity(profile_id):
    """Four bounded requests; absent evidence remains unknown, never fabricated."""
    profile_id = str(profile_id)
    if not profile_id.isdigit() or len(profile_id) > 20:
        return dict(records=[], available=False)
    deadline = time.monotonic() + 12
    jobs, records, available = {}, {}, False
    try:
        for board in (1, 2, 3, 4):
            if not _slots.acquire(blocking=False):
                continue
            url = f'https://aomstats.io/profile/{profile_id}?leaderboard={board}'
            try:
                job = _pool.submit(_fetch_document, url, deadline)
            except Exception:
                _slots.release()
                raise
            job.add_done_callback(lambda _: _slots.release())
            jobs[job] = url
        try:
            for job in as_completed(jobs, timeout=max(0, deadline - time.monotonic())):
                try:
                    page = job.result()
                    if page.get('error') or not page.get('html'):
                        continue
                    parsed = parse_activity(page['html'], profile_id)
                    available = True
                    for item in parsed:
                        item['source_url'] = jobs[job]
                        records.setdefault(item['match_id'], item)
                except (ValueError, TypeError):
                    continue
        except TimeoutError:
            pass
    finally:
        for job in jobs:
            job.cancel()
    return dict(records=list(records.values()), available=available)
