"""Presence is current evidence, expires, and is shared across server workers."""
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
import requests
import aom_presence as presence
import test_v22_flows as fixtures
import test_arena_v24 as teams

site = fixtures.site
STAMP = 1789265467
DOCUMENT = (Path(__file__).parent/'fixtures/aomstats_lobbies_presence.html').read_text()


class ParsingTests(unittest.TestCase):
    def test_three_lists_use_human_ids_not_names_history_ai_or_placeholders(self):
        for source in ('ranked','customs'):
            data = presence.parse_lobbies(DOCUMENT,source,STAMP+1)
            self.assertEqual(data['players'],{'1001':'match','1002':'match'})
        data = presence.parse_lobbies(DOCUMENT,'open',STAMP+1)
        self.assertEqual(data['players'],{'1003':'lobby'})

    def test_empty_is_a_valid_snapshot_but_errors_and_stale_pages_are_not(self):
        empty='<script>{metadata:{lastLobbyTime:%d},lobbies:[]}</script>'%STAMP
        self.assertEqual(presence.parse_lobbies(empty,'open',STAMP)['players'],{})
        for html,now in [('<h1>Service unavailable</h1>',STAMP),
                         ('<script>{lobbies:[]}</script>',STAMP),
                         (DOCUMENT,STAMP+180),(DOCUMENT,STAMP-61),
                         ('<script>{metadata:{lastLobbyTime:%d},lobbies:[</script>'%STAMP,STAMP)]:
            with self.subTest(html=html[:60],now=now),self.assertRaises(ValueError):
                presence.parse_lobbies(html,'open',now)

    def test_network_timeout_redirects_and_size_budget_are_bounded(self):
        with patch.object(presence.requests,'get',side_effect=requests.Timeout):
            with self.assertRaises(requests.Timeout):presence.fetch_source('open')
        with patch.object(presence.requests,'get') as get:
            response=get.return_value.__enter__.return_value
            response.status_code=302
            with self.assertRaises(ValueError):presence.fetch_source('open')
            self.assertFalse(get.call_args.kwargs['allow_redirects'])
            response.status_code=200
            response.iter_content.return_value=[b'x'*(presence.MAX_BYTES+1)]
            with self.assertRaises(ValueError):presence.fetch_source('open')
            self.assertTrue(get.return_value.__exit__.called)


class PresenceFlows(unittest.TestCase):
    setUp = teams.TeamFlows.setUp
    login = fixtures.SiteFlows.login
    post = fixtures.SiteFlows.post
    row = fixtures.SiteFlows.row
    make_team = teams.TeamFlows.make_team

    def fake_source(self, source):
        return {'players':{'1001':'match'} if source=='ranked' else
                         {'1002':'match'} if source=='customs' else {'1003':'lobby'},
                'source_at':presence.time.time()}

    def test_public_api_maps_to_site_ids_and_excludes_inactive_and_unlinked_players(self):
        with site.app.app_context():
            db=site.get_db()
            db.execute('UPDATE players SET is_active=0 WHERE id=?',(self.players[1],))
            db.execute("UPDATE players SET aomstats_profile_id='' WHERE id=?",(self.players[3],))
            db.commit()
        with patch.object(presence,'fetch_source',side_effect=self.fake_source) as fetch:
            result=self.client.get('/api/arena/presenca')
        self.assertEqual(result.status_code,200)
        self.assertEqual(fetch.call_count,3)
        self.assertIn('no-store',result.headers['Cache-Control'])
        data=result.get_json()['players']
        self.assertEqual(set(data),{str(self.players[0]),str(self.players[2])})
        self.assertEqual(data[str(self.players[2])]['state'],'lobby')
        self.assertLessEqual(data[str(self.players[0])]['expires_in'],90)

    def test_cache_and_lease_are_shared_between_independent_connections(self):
        seen=[]
        def fetch(source):
            with sqlite3.connect(site.DB_PATH) as other:
                other.row_factory=sqlite3.Row
                # A different worker during the refresh does not launch more HTTP work.
                seen.append(presence.snapshot(other))
            return self.fake_source(source)
        with patch.object(presence,'fetch_source',side_effect=fetch) as mocked:
            first=self.client.get('/api/arena/presenca').get_json()
            second=self.client.get('/api/arena/presenca').get_json()
            self.assertEqual(mocked.call_count,3)
        self.assertEqual(seen,[{}, {}, {}])
        self.assertEqual(first['players'],second['players'])

    def test_leaving_disappears_and_failures_cannot_extend_old_confirmations(self):
        now=[STAMP]
        with patch.object(presence.time,'time',side_effect=lambda:now[0]):
            with patch.object(presence,'fetch_source',side_effect=self.fake_source):
                self.assertEqual(len(self.client.get('/api/arena/presenca').get_json()['players']),3)
            now[0]+=45
            with patch.object(presence,'fetch_source',side_effect=requests.Timeout) as fetch:
                self.assertEqual(len(self.client.get('/api/arena/presenca').get_json()['players']),3)
                self.client.get('/api/arena/presenca')
                self.assertEqual(fetch.call_count,3)
                now[0]+=45
                self.assertEqual(self.client.get('/api/arena/presenca').get_json()['players'],{})
            now[0]+=45
            with patch.object(presence,'fetch_source',side_effect=self.fake_source):
                self.assertEqual(len(self.client.get('/api/arena/presenca').get_json()['players']),3)
            now[0]+=45
            with patch.object(presence,'fetch_source',return_value={'players':{},'source_at':now[0]}):
                self.assertEqual(self.client.get('/api/arena/presenca').get_json()['players'],{})

    def test_provider_timestamp_limits_ttl_and_newer_room_supersedes_older_match(self):
        def fetch(source):
            return {'players':{'1001':'lobby' if source=='open' else 'match'},
                    'source_at':STAMP-150 if source=='open' else STAMP-160}
        with patch.object(presence.time,'time',return_value=STAMP),patch.object(presence,'fetch_source',side_effect=fetch):
            item=self.client.get('/api/arena/presenca').get_json()['players'][str(self.players[0])]
        self.assertEqual(item,{'state':'lobby','expires_in':30})

    def test_schema_is_idempotent_and_preserves_rankings_duels_and_photos(self):
        with site.app.app_context():
            db=site.get_db()
            site.arena_seasons.record_result(db,'x1',100,[self.players[0]],[self.players[1]])
            before=[tuple(r) for r in db.execute('SELECT * FROM arena_results')]
            before_players=[tuple(r) for r in db.execute('SELECT * FROM players')]
            presence.init_cache(db);presence.init_cache(db)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_results')],before)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM players')],before_players)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM aom_presence_cache').fetchone()[0],3)

    def test_markers_cover_profiles_modal_rankings_and_teams_without_fetching_on_render(self):
        team=self.make_team(0,[1],'Dupla presente')
        urls=['/x1','/comunidade','/arena/temporadas',f'/perfil/{self.players[0]}',
              f'/perfil/{self.players[0]}/card','/arena/2x2',f'/arena/equipe/{team}']
        # Discover actual team/season routes from Flask to avoid asserting aliases.
        with site.app.test_request_context():
            urls[2]=site.url_for('arena_seasons_page')
            urls[-2]=site.url_for('teams_arena')
            urls[-1]=site.url_for('teams_profile',tid=team)
        with patch.object(presence,'fetch_source',side_effect=AssertionError('No HTTP during HTML rendering')):
            for url in urls:
                response=self.client.get(url)
                self.assertEqual(response.status_code,200,url)
                soup=BeautifulSoup(response.data,'html.parser')
                self.assertIsNotNone(soup.select_one('[data-aom-player]'),url)
                self.assertFalse(soup.select('[data-aom-state]'),url)
        soup=BeautifulSoup(self.client.get('/x1').data,'html.parser')
        self.assertEqual(len(soup.select('.social-player-avatar[data-aom-player]')),6)
        self.assertIsNotNone(soup.select_one('.monthly-ranking-row .rank-avatar'))
        self.assertIsNotNone(soup.select_one('.monthly-ranking-row .rank-emblem'))
