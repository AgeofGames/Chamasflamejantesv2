"""Regression cases grounded in public AoMStats cards captured on 2026-09-09."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import aomstats_matches as lookup

FIXTURES = Path(__file__).parent / 'fixtures'
CUSTOM = (FIXTURES / 'aomstats_custom_43115933.html').read_text()
RANKED = (FIXTURES / 'aomstats_ranked_38263962.html').read_text()
PAIR = ['1076869557', '1076393730']


class MatchLookupTests(unittest.TestCase):
    def lookup_custom(self, html=CUSTOM, pair=PAIR):
        def fetch(url, deadline):
            return {'html': html if '?leaderboard=0' in url else '<h1>Match not found</h1>'}
        with patch.object(lookup, '_fetch_document', side_effect=fetch):
            return lookup.lookup_match('43115933', pair)

    def test_actual_custom_match_despite_missing_detail_page(self):
        result = self.lookup_custom()
        self.assertEqual(result['state'], 'completed')
        self.assertEqual(result['winner_profile_id'], PAIR[0])
        self.assertEqual(result['loser_profile_id'], PAIR[1])
        self.assertEqual((result['map'], result['duration']), ('Mirage', 368))
        self.assertIn('?leaderboard=0', result['match_url'])
        self.assertEqual(result['source'], 'customs_quickplay')

    def test_actual_ranked_match_is_still_supported(self):
        def fetch(url, deadline): return {'html': RANKED if '/match/' in url else ''}
        with patch.object(lookup, '_fetch_document', side_effect=fetch):
            result = lookup.lookup_match('38263962', [PAIR[0], '1077436368'])
        self.assertEqual(result['state'], 'completed')
        self.assertEqual((result['winner_profile_id'], result['map'], result['duration']), (PAIR[0], 'Alfheim', 786))

    def test_wrong_profiles_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'dois perfis'):
            self.lookup_custom(pair=['1001', '1002'])

    def test_ai_or_third_player_is_not_a_valid_x1(self):
        extra = '<div><img alt="Zeus portrait"><span>AI Player</span><svg class="text-stats-low"></svg></div>'
        html = CUSTOM.replace('<h3>Mirage</h3>', '<h3>Mirage</h3>' + extra)
        with self.assertRaisesRegex(ValueError, 'X1'):
            self.lookup_custom(html)

    def test_missing_result_is_not_inferred_from_other_player(self):
        result = self.lookup_custom(CUSTOM.replace('text-stats-low', 'result-not-ready'))
        self.assertEqual(result['state'], 'pending')
        self.assertIn('Partida encontrada', result['message'])

    def test_out_of_sync_is_not_registered(self):
        html = CUSTOM.replace('>', '><p>OUT OF SYNC</p>', 1)
        with self.assertRaisesRegex(ValueError, 'dessincroniza'):
            self.lookup_custom(html)

    def test_neighboring_matches_and_id_prefixes_do_not_leak(self):
        neighbor = CUSTOM.replace('43115933', '431159330').replace('1076869557', '1111111111')
        parsed = lookup.parse_match_page('43115933', neighbor + CUSTOM)
        self.assertEqual({row['profile_id'] for row in parsed['players']}, set(PAIR))
        self.assertFalse(lookup.parse_match_page('431159', CUSTOM)['found'])

    def test_serialized_fields_need_no_specific_order_or_eval(self):
        source = '''<script>const data={matches:[
          {profile_id:1076393730, win:false, nickname:"match_id:43115933,profile_id:999,win:true", match_id:43115933,mapname:"Mirage",duration:368},
          {"win":true,"match_id":43115933,"profile_id":1076869557,"mapname":"Mirage","duration":368},
          {match_id:431159330,profile_id:123,win:true}
        ]};</script>'''
        parsed = lookup.parse_match_page('43115933', source)
        self.assertEqual(parsed['participant_count'], 2)
        self.assertEqual({row['profile_id'] for row in parsed['players']}, set(PAIR))
        self.assertEqual(next(p['win'] for p in parsed['players'] if p['profile_id'] == PAIR[0]), True)

    def test_absent_match_returns_a_finished_lookup(self):
        with patch.object(lookup, '_fetch_document', return_value={'html': '<h1>Match not found</h1>'}):
            result = lookup.lookup_match('43115933', PAIR)
        self.assertEqual(result['state'], 'pending')
        self.assertIn('consulta já terminou', result['message'])

    def test_overall_deadline_does_not_wait_for_stuck_network_workers(self):
        release = threading.Event()
        pool = ThreadPoolExecutor(max_workers=3)
        def blocked(*args):
            release.wait(3)
            return {'html': ''}
        try:
            with patch.object(lookup, '_pool', pool), patch.object(lookup, '_slots', threading.BoundedSemaphore(3)), \
                 patch.object(lookup, 'LOOKUP_TIMEOUT', .06), patch.object(lookup, '_fetch_document', side_effect=blocked):
                started = time.monotonic()
                result = lookup.lookup_match('43115933', PAIR)
                elapsed = time.monotonic() - started
                release.set()
                pool.shutdown(wait=True)
            self.assertLess(elapsed, .5)
            self.assertEqual(result['state'], 'unavailable')
        finally:
            release.set()
            pool.shutdown(wait=True)

    def test_oversize_response_is_closed(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 200
        response.iter_content.return_value = iter([b'x' * 65])
        with patch.object(lookup.requests, 'get', return_value=response), patch.object(lookup, 'MAX_DOCUMENT_BYTES', 64):
            result = lookup._fetch_document('https://aomstats.io/match/43115933', time.monotonic() + 1)
        self.assertTrue(result['error'])
        response.__exit__.assert_called_once()


if __name__ == '__main__': unittest.main()
