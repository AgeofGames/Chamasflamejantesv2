"""Integration checks using an isolated SQLite database and mocked external services.

Run: python -m unittest discover -s tests -v
"""
import gzip
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_initial = tempfile.TemporaryDirectory(prefix='chamas-v22-import-')
os.environ['DATABASE_PATH'] = str(Path(_initial.name) / 'initial.sqlite')
os.environ.setdefault('FFA_SECRET_KEY', 'isolated-test-key')
import app as site
from bs4 import BeautifulSoup
from PIL import Image


class SiteFlows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='chamas-v22-test-')
        self.addCleanup(self.tmp.cleanup)
        site.DB_PATH = Path(self.tmp.name) / 'test.sqlite'
        site.UPLOAD_DIR = Path(self.tmp.name) / 'uploads'
        site.UPLOAD_DIR.mkdir()
        site.init_db()
        site.migrate_v6_db()
        site.app.config.update(TESTING=True)
        self.client = site.app.test_client()
        self.players, self.accounts = [], []
        with site.app.app_context():
            db = site.get_db()
            db.execute("INSERT OR REPLACE INTO site_meta(key,value) VALUES('site_creator_attempted_at',CURRENT_TIMESTAMP)")
            for i, name in enumerate(['Makise_Kurisu_00','André','Visitante']):
                pid = db.execute('INSERT INTO players(nickname,aomstats_profile_id,aomstats_url) VALUES(?,?,?)',
                    (name,str(1001+i),f'https://aomstats.io/profile/{1001+i}')).lastrowid
                aid = db.execute('INSERT INTO social_accounts(google_sub,email,player_id) VALUES(?,?,?)',
                    (f'google-{i}',f'p{i}@example.test',pid)).lastrowid
                db.execute('INSERT INTO community_members(player_id,community_elo) VALUES(?,0)',(pid,))
                self.players.append(pid); self.accounts.append(aid)
            self.tid = db.execute("""INSERT INTO tournaments(slug,name,short_name,mode_key,format_type,
                team_size,best_of,max_entries,registration_open,status,is_public)
                VALUES('teste','Torneio de teste','Teste','1v1_round_robin','round_robin',1,1,8,1,'inscricoes',1)""").lastrowid
            db.commit()

    def login(self, index=0):
        with self.client.session_transaction() as session:
            session['social_account_id'] = self.accounts[index]
            session['_csrf'] = 'csrf-test'

    def post(self, path, **data):
        return self.client.post(path, data={'_csrf':'csrf-test', **data})

    def row(self, sql, values=()):
        with site.app.app_context():
            result = site.get_db().execute(sql,values).fetchone()
            return dict(result) if result else None

    def create_challenge(self):
        self.login()
        response = self.post(f'/perfil/{self.players[1]}/desafiar', message='Batalha de teste')
        self.assertEqual(response.status_code,302)
        return self.row('SELECT * FROM social_duels ORDER BY id DESC LIMIT 1')

    def test_public_routes_and_all_builds(self):
        urls=['/','/torneios','/historico','/comunidade','/x1','/x1/historico','/programas','/mapas',
              '/feedback','/entrar','/conhecimento','/conhecimento/build-orders','/conhecimento/counters',
              '/conhecimento/guia-de-teclas',f'/perfil/{self.players[0]}','/torneio/teste',
              '/torneio/teste/participantes','/torneio/teste/confrontos']
        for url in urls:
            with self.subTest(url=url):
                r=self.client.get(url)
                self.assertEqual(r.status_code,200)
                soup=BeautifulSoup(r.data,'html.parser')
                self.assertIsNotNone(soup.select_one('#main-navigation'))
                self.assertIsNotNone(soup.select_one('#main-content'))
                self.assertIn('private',r.headers['Cache-Control'])
        with site.app.test_request_context():
            builds=[site.url_for('knowledge_build_page',god_slug=site.slugify(b['god']),build_id=b['id']) for b in site.knowledge_catalog()['builds']]
        for url in builds:
            with self.subTest(build=url): self.assertEqual(self.client.get(url).status_code,200)

    def test_static_compression_cache_and_negotiation(self):
        with site.app.test_request_context():
            url=site.url_for('static',filename='experience.css')
        plain=self.client.get(url,headers={'Accept-Encoding':'gzip;q=0'})
        compressed=self.client.get(url,headers={'Accept-Encoding':'gzip'})
        self.assertEqual(gzip.decompress(compressed.data),plain.data)
        self.assertLess(len(compressed.data),len(plain.data)/2)
        self.assertNotIn('Content-Encoding',plain.headers)
        self.assertIn('immutable',compressed.headers['Cache-Control'])
        self.assertIn('Accept-Encoding',compressed.headers['Vary'])
        with self.client.get(url,headers={'If-None-Match':plain.headers['ETag']}) as cached:
            self.assertEqual(cached.status_code,304)
        partial=self.client.get(url,headers={'Range':'bytes=0-9','Accept-Encoding':'gzip'})
        self.assertEqual(partial.status_code,206)
        self.assertEqual(partial.data,plain.data[:10])
        plain.close(); compressed.close(); partial.close()

    def test_arena_roster_flags_and_batched_stats(self):
        a,b=self.players[:2]
        with site.app.test_request_context():
            db=site.get_db()
            for i,winner in enumerate([a,b,a,a]):
                loser=b if winner==a else a
                db.execute("INSERT INTO social_duels(challenger_id,challenged_id,status,winner_id,loser_id,share_token) VALUES(?,?,'completed',?,?,?)",(a,b,winner,loser,f'win-{i}'))
            db.execute("INSERT INTO social_duels(challenger_id,challenged_id,status,share_token) VALUES(?,?,'refused','refusal')",(b,a))
            db.commit()
            sql=[]; db.set_trace_callback(sql.append)
            ranking=site.duel_ranking()
            player=next(p for p in ranking if p['id']==a)
            self.assertEqual(player['stats']['wins'],3)
            self.assertEqual(player['stats']['losses'],1)
            self.assertEqual(player['stats']['streak'],2)
            self.assertEqual(player['stats']['refusals'],1)
            self.assertEqual(player['social_enabled'],1)
            self.assertEqual(len(sql),2)

    def test_challenge_repeated_submission_and_csrf(self):
        duel=self.create_challenge()
        self.post(f'/perfil/{self.players[1]}/desafiar')
        self.assertEqual(self.row('SELECT COUNT(*) c FROM social_duels')['c'],1)
        response=self.client.post(f"/duelo/{duel['id']}/cancelar",data={})
        self.assertEqual(response.status_code,400)
        self.assertIsNotNone(self.row('SELECT * FROM social_duels'))

    def test_challenger_cancel_deletes_notifications_and_links(self):
        duel=self.create_challenge()
        self.login(1)
        self.assertEqual(self.post(f"/duelo/{duel['id']}/cancelar").status_code,403)
        self.login(0)
        self.assertIn(b'CANCELAR DESAFIO',self.client.get(f"/duelo/{duel['id']}").data)
        self.post(f"/duelo/{duel['id']}/cancelar")
        self.assertIsNone(self.row('SELECT * FROM social_duels'))
        self.assertIsNone(self.row('SELECT * FROM social_notifications'))
        self.assertEqual(self.client.get(f"/arena/desafio/{duel['share_token']}").status_code,404)

    def test_accept_and_refuse_are_exclusive(self):
        duel=self.create_challenge(); self.login(1)
        self.post(f"/duelo/{duel['id']}/aceitar")
        self.post(f"/duelo/{duel['id']}/recusar")
        self.assertEqual(self.row('SELECT * FROM social_duels')['status'],'accepted')
        self.assertEqual(self.row("SELECT COUNT(*) c FROM social_notifications WHERE kind='accepted'")['c'],1)
        self.login(0); self.post(f"/duelo/{duel['id']}/cancelar")
        self.assertEqual(self.row('SELECT * FROM social_duels')['status'],'accepted')

    def test_match_pending_then_completed_and_duplicate_check(self):
        duel=self.create_challenge(); self.login(1); self.post(f"/duelo/{duel['id']}/aceitar")
        pending={'state':'pending','match_url':'https://aomstats.io/match/12345678','message':'Aguardando resultado'}
        result={'state':'completed','match_url':pending['match_url'],'winner_profile_id':'1001','loser_profile_id':'1002','map':'Alfheim','duration':1200}
        with patch.object(site,'fetch_aomstats_match',return_value=pending):
            self.post(f"/duelo/{duel['id']}/partida",match_id='12345678')
        self.assertEqual(self.row('SELECT * FROM social_duels')['status'],'match_pending')
        stale=self.row('SELECT * FROM social_duels')
        with patch.object(site,'fetch_aomstats_match',return_value=result):
            self.post(f"/duelo/{duel['id']}/verificar")
        self.assertEqual(self.row('SELECT * FROM social_duels')['winner_id'],self.players[0])
        with site.app.test_request_context():
            site.verify_social_duel_match(stale,fetched_result=result)
            site.verify_social_duel_match(stale,fetched_result=pending)
        self.assertEqual(self.row('SELECT * FROM social_duels')['status'],'completed')
        self.assertEqual(self.row("SELECT COUNT(*) c FROM social_notifications WHERE kind='result'")['c'],2)

    def test_other_players_cannot_respond_or_submit_match(self):
        duel=self.create_challenge(); self.login(2)
        for action in ['aceitar','recusar','cancelar','partida','verificar']:
            self.assertEqual(self.post(f"/duelo/{duel['id']}/{action}",match_id='12345678').status_code,403)

    def test_notification_feed_is_private_and_updates(self):
        self.assertEqual(self.client.get('/api/notificacoes').status_code,401)
        self.create_challenge(); self.login(1)
        r=self.client.get('/api/notificacoes'); data=r.get_json()
        self.assertEqual(data['unread'],1)
        self.assertIn('ACEITAR',data['html'])
        self.assertIn('no-store',r.headers['Cache-Control'])
        self.assertEqual(self.client.get('/api/notificacoes?cursor='+data['cursor']).status_code,204)
        self.post('/notificacoes',next='/x1')
        self.assertEqual(self.client.get('/api/notificacoes').get_json()['unread'],0)

    def test_profile_quote_and_avatar_save_without_aomstats(self):
        self.login()
        image=io.BytesIO(); Image.new('RGB',(1200,900),'orange').save(image,'PNG'); image.seek(0)
        with patch.object(site,'fetch_aomstats',side_effect=AssertionError('No external call expected')):
            r=self.post('/meu-perfil/editar',aomstats_url='https://aomstats.io/profile/1001',quote='Minha frase',avatar_mode='keep',avatar=(image,'avatar.png'))
        self.assertEqual(r.status_code,302)
        player=self.row('SELECT * FROM players WHERE id=?',(self.players[0],))
        self.assertEqual(player['quote'],'Minha frase')
        with Image.open(site.UPLOAD_DIR / Path(player['avatar_file']).name) as saved:
            self.assertLessEqual(max(saved.size),512)
        self.assertEqual(self.client.get('/perfil').status_code,302)

    def test_tournament_registration_uses_current_profile_only(self):
        self.login()
        self.post('/torneio/teste/inscricao',player_id=str(self.players[1]))
        self.post('/torneio/teste/inscricao')
        entry=self.row('SELECT * FROM tournament_entries')
        self.assertEqual(entry['player_id'],self.players[0])
        self.assertEqual(self.row('SELECT COUNT(*) c FROM tournament_entries')['c'],1)

    def test_feedback_map_request_and_download(self):
        self.login()
        self.post('/feedback',aomstats_url='https://aomstats.io/profile/1001',message='Ótimo feedback de teste')
        self.post('/mapas/pedir',aomstats_url='https://aomstats.io/profile/1001',category='FFA',message='Mapa com oito ilhas')
        self.assertIsNotNone(self.row('SELECT * FROM feedback_entries'))
        self.assertIsNotNone(self.row('SELECT * FROM map_requests'))

    def test_google_callback_state_and_identity(self):
        self.assertEqual(self.client.get('/auth/google/callback?state=wrong&code=x').status_code,400)
        with self.client.session_transaction() as session: session['google_oauth_state']='valid-state'
        with patch.object(site,'_google_profile_from_code',return_value={'sub':'new-google','email':'new@example.test','name':'Novo Jogador'}):
            r=self.client.get('/auth/google/callback?state=valid-state&code=test')
        self.assertEqual(r.status_code,302)
        self.assertIn('/meu-perfil/configurar',r.location)
        self.assertIsNotNone(self.row("SELECT * FROM social_accounts WHERE google_sub='new-google'"))

    def test_sitemap_and_shared_profile_metadata(self):
        self.assertEqual(self.client.get('/sitemap.xml').status_code,200)
        self.assertIn(b'Sitemap:',self.client.get('/robots.txt').data)
        soup=BeautifulSoup(self.client.get(f'/perfil/{self.players[0]}').data,'html.parser')
        self.assertIn('Makise',soup.select_one('meta[property="og:title"]')['content'])
        self.assertTrue(soup.select_one('meta[property="og:image"]')['content'].startswith('https://'))


if __name__ == '__main__':
    unittest.main()
