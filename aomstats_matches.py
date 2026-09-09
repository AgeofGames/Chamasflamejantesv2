"""Read public AoMStats match pages and Customs/Quickplay profile cards.

No script evaluation and no result inferred from nicknames or missing flags.
Network work is bounded independently from the request serving the duel page.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import ast
import json
import re
import threading
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import requests

LOOKUP_TIMEOUT = 12.0
MAX_DOCUMENT_BYTES = 3 * 1024 * 1024
_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix='aom-match')
_slots = threading.BoundedSemaphore(6)
_tokens = re.compile(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|-?\d+(?:\.\d+)?|[A-Za-z_$][\w$]*|[{}\[\]:,]''')
_profile_path = re.compile(r'^/profile/(\d+)/?$')
_id_text = re.compile(r'^\s*ID:\s*(\d+)\s*$', re.I)


def _scalar(token):
    if token == 'true': return True
    if token == 'false': return False
    if token == 'null': return None
    if token.startswith('"'):
        try: return json.loads(token)
        except ValueError: return None
    if token.startswith("'"):
        try: return ast.literal_eval(token)
        except (ValueError, SyntaxError): return None
    if re.fullmatch(r'-?\d+', token): return int(token)
    return None


def _serialized_records(script):
    """Read scalar object fields from JSON/Svelte literals without executing JS."""
    stack = []
    for match in _tokens.finditer(script):
        token = match.group()
        if token in ('{', '['):
            if stack and stack[-1]['state'] == 'value':
                stack[-1]['state'] = 'separator'
            stack.append({'kind': token, 'state': 'key', 'key': None, 'fields': {}})
            continue
        if token in ('}', ']'):
            if not stack: continue
            frame = stack.pop()
            if frame['kind'] == '{' and 'match_id' in frame['fields']:
                yield frame['fields']
            continue
        if not stack or stack[-1]['kind'] != '{': continue
        frame = stack[-1]
        if token == ',':
            frame['state'] = 'key'
        elif frame['state'] == 'key':
            frame['key'] = _scalar(token) if token[:1] in ('"', "'") else token
            frame['state'] = 'colon'
        elif frame['state'] == 'colon' and token == ':':
            frame['state'] = 'value'
        elif frame['state'] == 'value':
            if isinstance(frame['key'], str): frame['fields'][frame['key']] = _scalar(token)
            frame['state'] = 'separator'


def _profile_id(link):
    url = urlparse(link.get('href', ''))
    if url.netloc and url.netloc != 'aomstats.io': return None
    match = _profile_path.fullmatch(url.path)
    return match.group(1) if match else None


def _parse_card(card):
    players = []
    portraits = card.select('img[alt$=" portrait"]')
    for portrait in portraits:
        row = portrait.parent
        # A player row has one god portrait and one profile. Never ascend into
        # a whole team/card and accidentally give its first player another win.
        for _ in range(5):
            if row is None or row is card: break
            if len(row.select('img[alt$=" portrait"]')) != 1: break
            links = [a for a in row.find_all('a', href=True) if _profile_id(a)]
            if links:
                if len(links) != 1: break
                wins = row.select('svg.text-stats-high')
                losses = row.select('svg.text-stats-low')
                won = True if len(wins) == 1 and not losses else False if len(losses) == 1 and not wins else None
                players.append({'profile_id': _profile_id(links[0]), 'win': won})
                break
            row = row.parent
    clock = next((s.get_text(strip=True) for s in card.select('span.font-mono')
                  if re.fullmatch(r'\d{1,3}:\d{2}(?::\d{2})?', s.get_text(strip=True))), '')
    duration = 0
    for value in clock.split(':') if clock else []: duration = duration * 60 + int(value)
    heading = card.find(['h1', 'h3'])
    return {
        'found': True, 'players': players, 'participant_count': len(portraits),
        'map': heading.get_text(' ', strip=True) if heading else '', 'duration': duration,
        'out_of_sync': any(s.strip() == 'OUT OF SYNC' for s in card.stripped_strings),
    }


def parse_match_page(match_id, document):
    target = str(match_id)
    soup = BeautifulSoup(document, 'html.parser')
    for marker in soup.find_all(string=_id_text):
        if _id_text.fullmatch(marker).group(1) != target: continue
        card = marker.parent
        for _ in range(12):
            if card is None: break
            headings = card.find_all(['h1', 'h2', 'h3'])
            if len(headings) > 1: break
            if headings and card.select('img[alt$=" portrait"]'):
                # Include a possible OUT OF SYNC banner outside the inner layout.
                parent = card.parent
                if parent and len(parent.find_all(['h1', 'h2', 'h3'])) == 1:
                    ids = {_id_text.fullmatch(s).group(1) for s in parent.find_all(string=_id_text)}
                    if ids == {target}: card = parent
                return _parse_card(card)
            card = card.parent

    scripts = [s.get_text() for s in soup.find_all('script')]
    if '<' not in document[:100]: scripts.append(document)
    rows, metadata, conflicting = {}, {}, False
    for script in scripts:
        for record in _serialized_records(script):
            if str(record.get('match_id')) != target: continue
            profile_id = str(record.get('profile_id', ''))
            if not profile_id.isdigit(): continue
            won = record.get('win')
            if type(won) is not bool:
                result_type = record.get('resulttype')
                won = bool(result_type) if type(result_type) is int and result_type in (0, 1) else None
            if profile_id in rows and rows[profile_id]['win'] != won: conflicting = True
            rows[profile_id] = {'profile_id': profile_id, 'win': won}
            metadata = record
    return {
        'found': bool(rows), 'players': list(rows.values()), 'participant_count': len(rows),
        'map': str(metadata.get('mapname') or ''), 'duration': int(metadata.get('duration') or 0),
        'out_of_sync': conflicting,
    }


def _fetch_document(url, deadline):
    if time.monotonic() >= deadline: return {'error': True}
    try:
        # Each response is closed even when it exceeds the byte/time budget.
        with requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; ChamasFlamejantes/22.2)',
            'Accept': 'text/html', 'Accept-Language': 'en-US,en;q=0.9',
        }, timeout=(2, 4), stream=True, allow_redirects=False) as response:
            if response.status_code == 404: return {'html': ''}
            if response.status_code != 200: return {'error': True}
            chunks, size = [], 0
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_DOCUMENT_BYTES or time.monotonic() >= deadline:
                    return {'error': True}
                chunks.append(chunk)
            return {'html': b''.join(chunks).decode('utf-8', errors='replace')}
    except requests.RequestException:
        return {'error': True}


def lookup_match(match_id, expected_profile_ids):
    match_id = str(match_id).strip()
    expected = {str(value) for value in expected_profile_ids}
    if not re.fullmatch(r'\d{5,12}', match_id): raise ValueError('Informe um ID de partida válido.')
    if len(expected) != 2 or any(not value.isdigit() for value in expected):
        raise ValueError('Os dois jogadores precisam vincular seus perfis AoMStats.')
    match_url = f'https://aomstats.io/match/{match_id}'
    sources = [match_url] + [f'https://aomstats.io/profile/{pid}?leaderboard=0' for pid in sorted(expected)]
    deadline = time.monotonic() + LOOKUP_TIMEOUT
    jobs, had_error, found_pending = {}, False, None
    try:
        for url in sources:
            if not _slots.acquire(blocking=False):
                had_error = True
                continue
            try: job = _pool.submit(_fetch_document, url, deadline)
            except Exception:
                _slots.release()
                raise
            job.add_done_callback(lambda _: _slots.release())
            jobs[job] = url
        try:
            for job in as_completed(jobs, timeout=max(0, deadline - time.monotonic())):
                try: page = job.result()
                except Exception:
                    had_error = True
                    continue
                if page.get('error'):
                    had_error = True
                    continue
                try: parsed = parse_match_page(match_id, page.get('html', ''))
                except (TypeError, ValueError):
                    had_error = True
                    continue
                if not parsed['found']: continue
                rows = parsed['players']
                if parsed['out_of_sync']:
                    raise ValueError('O AoMStats não confirma um resultado válido para esta partida (dessincronização ou dados conflitantes). Informe o ID de outra partida concluída.')
                if parsed['participant_count'] != 2 or len(rows) != 2 or {p['profile_id'] for p in rows} != expected:
                    raise ValueError('Esse ID não é uma partida X1 entre os dois perfis deste desafio.')
                winners = [p for p in rows if p['win'] is True]
                losers = [p for p in rows if p['win'] is False]
                if len(winners) == 1 and len(losers) == 1:
                    return {
                        'state': 'completed', 'match_url': jobs[job], 'match_id': match_id,
                        'source': 'customs_quickplay' if '?leaderboard=0' in jobs[job] else 'match',
                        'winner_profile_id': winners[0]['profile_id'], 'loser_profile_id': losers[0]['profile_id'],
                        'map': parsed['map'], 'duration': parsed['duration'],
                    }
                found_pending = jobs[job]
        except TimeoutError:
            had_error = True
    finally:
        for job in jobs: job.cancel()
    if found_pending:
        return {'state': 'pending', 'match_url': found_pending,
                'message': 'Partida encontrada, mas o AoMStats ainda não confirmou o vencedor e o derrotado. A consulta terminou; tente novamente mais tarde.'}
    if had_error:
        return {'state': 'unavailable', 'match_url': match_url,
                'message': 'Não foi possível concluir a consulta ao AoMStats dentro do limite de tempo. Seu ID foi preservado. Tente novamente em alguns instantes.'}
    return {'state': 'pending', 'match_url': sources[1],
            'message': 'ID não encontrado na página da partida nem nas partidas recentes de Customs/Quickplay dos dois perfis. Confira o número ou tente novamente mais tarde; a consulta já terminou.'}
