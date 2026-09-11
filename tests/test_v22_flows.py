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

    def test_default_link_preview_is_public_and_complete(self):
        from urllib.parse import urlsplit
        crawler = self.client
        headers = {'User-Agent': 'WhatsApp/2.26', 'Accept-Encoding': 'gzip'}
        image_url = None
        for path in ['/', '/compartilhar', '/conhecimento', '/programas', '/mapas', '/x1']:
            with self.subTest(path=path):
                response = crawler.get(path, headers=headers)
                self.assertEqual(response.status_code, 200)
                soup = BeautifulSoup(response.data, 'html.parser')
                images = soup.select('head meta[property="og:image"]')
                self.assertEqual(len(images), 1)
                image_url = images[0]['content']
                self.assertEqual(image_url, site.PUBLIC_BASE_URL + '/capa-chamas-flamejantes.jpg')
                self.assertEqual(soup.select_one('meta[name="twitter:image"]')['content'], image_url)
                self.assertEqual(soup.select_one('meta[property="og:image:secure_url"]')['content'], image_url)
                self.assertEqual(soup.select_one('meta[property="og:image:width"]')['content'], '1200')
                self.assertEqual(soup.select_one('meta[property="og:image:height"]')['content'], '630')
                self.assertEqual(soup.select_one('meta[property="og:image:type"]')['content'], 'image/jpeg')
                self.assertEqual(soup.select_one('meta[property="og:url"]')['content'], site.PUBLIC_BASE_URL + path)
        parsed = urlsplit(image_url)
        image_path = parsed.path + '?' + parsed.query
        with crawler.get(image_path, headers=headers) as picture:
            self.assertEqual(picture.status_code, 200)
            self.assertEqual(picture.mimetype, 'image/jpeg')
            self.assertIn('public', picture.headers['Cache-Control'])
            self.assertNotIn('Set-Cookie', picture.headers)
            self.assertLess(len(picture.data), 300_000)
            with Image.open(io.BytesIO(picture.data)) as decoded:
                self.assertEqual(decoded.size, (1200, 630))
                self.assertEqual(decoded.format, 'JPEG')
            with crawler.head(image_path, headers=headers) as head:
                self.assertEqual(head.status_code, 200)
                self.assertEqual(head.content_length, len(picture.data))
        profile = BeautifulSoup(crawler.get(f'/perfil/{self.players[0]}').data, 'html.parser')
        self.assertNotEqual(profile.select_one('meta[property="og:image"]')['content'], image_url)
        duel = self.create_challenge()
        with crawler.session_transaction() as session:
            session.clear()
        invite = BeautifulSoup(crawler.get(f"/arena/desafio/{duel['share_token']}").data, 'html.parser')
        self.assertNotEqual(invite.select_one('meta[property="og:image"]')['content'], image_url)

    def test_new_share_link_opens_the_same_home_without_a_redirect(self):
        from urllib.robotparser import RobotFileParser
        home = self.client.get('/')
        shared = self.client.get('/compartilhar', headers={'User-Agent': 'WhatsApp/2.26'})
        self.assertEqual(shared.status_code, 200)
        self.assertNotIn('Location', shared.headers)
        root = BeautifulSoup(home.data, 'html.parser')
        new = BeautifulSoup(shared.data, 'html.parser')
        self.assertEqual(root.select_one('main').get_text(), new.select_one('main').get_text())
        self.assertEqual(new.select_one('meta[property="og:url"]')['content'], site.PUBLIC_BASE_URL + '/compartilhar')
        self.assertEqual(new.select_one('link[rel="canonical"]')['href'], site.PUBLIC_BASE_URL + '/')
        self.assertEqual(root.select_one('link[rel="canonical"]')['href'], site.PUBLIC_BASE_URL + '/')
        with site.app.test_request_context():
            self.assertEqual(site.url_for('home'), '/')
        share_button = new.select_one('.footer-tools [data-native-share]')
        self.assertEqual(share_button['data-share-url'], site.PUBLIC_BASE_URL + '/compartilhar')
        # The existing head metadata must be available before any JavaScript executes.
        self.assertLess(shared.data.index(b'property="og:image"'), 5000)
        rules = RobotFileParser()
        rules.parse(self.client.get('/robots.txt').get_data(as_text=True).splitlines())
        self.assertTrue(rules.can_fetch('WhatsApp', '/compartilhar'))
        self.assertTrue(rules.can_fetch('facebookexternalhit', '/capa-chamas-flamejantes.jpg'))

    def test_brand_icons_are_declared_and_accessible_without_a_session_or_database(self):
        from urllib.robotparser import RobotFileParser
        for path in ['/', '/compartilhar', '/conhecimento', f'/perfil/{self.players[0]}']:
            page = BeautifulSoup(self.client.get(path).data, 'html.parser')
            self.assertIsNotNone(page.select_one('link[rel="icon"][href="/favicon.ico"]'))
            self.assertIsNotNone(page.select_one('link[rel="icon"][href="/favicon.png"][sizes="96x96"]'))
            self.assertIsNotNone(page.select_one('link[rel="apple-touch-icon"][href="/apple-touch-icon.png"]'))
        rules = RobotFileParser()
        rules.parse(self.client.get('/robots.txt').get_data(as_text=True).splitlines())
        anon = site.app.test_client()
        assets = [('/favicon.ico', 'image/vnd.microsoft.icon', (256, 256)),
                  ('/favicon.png', 'image/png', (96, 96)),
                  ('/apple-touch-icon.png', 'image/png', (180, 180)),
                  ('/capa-chamas-flamejantes.jpg', 'image/jpeg', (1200, 630))]
        with patch.object(site, 'get_db', side_effect=AssertionError('Public image used the database')):
            for path, mime, size in assets:
                with self.subTest(path=path):
                    self.assertTrue(rules.can_fetch('Googlebot-Image', path))
                    with anon.get(path, headers={'User-Agent': 'Googlebot-Image/1.0'}) as asset:
                        self.assertEqual(asset.status_code, 200)
                        self.assertEqual(asset.mimetype, mime)
                        self.assertNotIn('Set-Cookie', asset.headers)
                        self.assertNotIn('Location', asset.headers)
                        self.assertIn('public', asset.headers['Cache-Control'])
                        with Image.open(io.BytesIO(asset.data)) as decoded:
                            self.assertEqual(decoded.size, size)
                            if path.endswith('.ico'):
                                self.assertTrue({(16,16),(32,32),(48,48),(96,96),(256,256)}.issubset(decoded.ico.sizes()))
                        with anon.head(path) as head:
                            self.assertEqual(head.status_code, 200)
                            self.assertEqual(head.content_length, len(asset.data))
                        with anon.get(path, headers={'If-None-Match':asset.headers['ETag']}) as cached:
                            self.assertEqual(cached.status_code, 304)

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
            # Two batched player/stat reads plus two monthly season reads.
            self.assertEqual(len(sql),4)

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

    def test_real_custom_card_registers_winner_via_json(self):
        import aomstats_matches
        fixture = (Path(__file__).parent / 'fixtures/aomstats_custom_43115933.html').read_text()
        with site.app.app_context():
            for pid, remote in zip(self.players, ['1076869557','1076393730']):
                site.get_db().execute('UPDATE players SET aomstats_profile_id=? WHERE id=?', (remote,pid))
            site.get_db().commit()
        duel = self.create_challenge(); self.login(1)
        self.post(f"/duelo/{duel['id']}/aceitar")
        def source(url, deadline): return {'html': fixture if '?leaderboard=0' in url else ''}
        with patch.object(aomstats_matches, '_fetch_document', side_effect=source):
            response = self.client.post(f"/duelo/{duel['id']}/partida", data={'_csrf':'csrf-test','match_id':'43115933'}, headers={'Accept':'application/json'})
        data = response.get_json()
        self.assertEqual(data['state'], 'completed')
        self.assertEqual(self.row('SELECT * FROM social_duels')['winner_id'], self.players[0])
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertEqual(self.row("SELECT COUNT(*) c FROM social_notifications WHERE kind='result'")['c'], 2)

    def test_json_lookup_unavailable_and_correct_id(self):
        duel = self.create_challenge(); self.login(1); self.post(f"/duelo/{duel['id']}/aceitar")
        unavailable = {'state':'unavailable', 'match_url':'https://aomstats.io/match/43115933', 'message':'Consulta encerrada; tente novamente.'}
        url = f"/duelo/{duel['id']}/partida"
        with patch.object(site,'fetch_aomstats_match', return_value=unavailable):
            for _ in range(2):
                response = self.client.post(url, data={'_csrf':'csrf-test','match_id':'43115933'}, headers={'Accept':'application/json'})
        data = response.get_json()
        self.assertEqual(data['state'], 'unavailable')
        self.assertEqual(data['redirect'], '')
        self.assertIn('Corrigir o ID', data['html'])
        self.assertIn('43115933', data['chat_html'])
        self.assertEqual(self.row("SELECT COUNT(*) c FROM social_notifications WHERE kind='match'")['c'], 1)
        with patch.object(site,'fetch_aomstats_match', side_effect=ValueError('ID de outros jogadores')):
            bad = self.client.post(url, data={'_csrf':'csrf-test','match_id':'43115934'}, headers={'Accept':'application/json'}).get_json()
        self.assertEqual(bad['state'], 'invalid')
        self.assertEqual(self.row('SELECT * FROM social_duels')['match_id'], '43115933')
        result = {'state':'completed','match_url':'https://aomstats.io/profile/1001?leaderboard=0','winner_profile_id':'1001','loser_profile_id':'1002','map':'Mirage','duration':368}
        with patch.object(site,'fetch_aomstats_match', return_value=result):
            good = self.client.post(url, data={'_csrf':'csrf-test','match_id':'43115934'}, headers={'Accept':'application/json'}).get_json()
        self.assertEqual(good['state'], 'completed')
        self.assertEqual(self.row('SELECT * FROM social_duels')['match_id'], '43115934')

    def test_wrong_stored_id_can_be_corrected_after_verify_error(self):
        duel = self.create_challenge(); self.login(1); self.post(f"/duelo/{duel['id']}/aceitar")
        with site.app.app_context():
            site.get_db().execute("UPDATE social_duels SET status='match_pending',match_id='43115933' WHERE id=?",(duel['id'],)); site.get_db().commit()
        with patch.object(site,'fetch_aomstats_match', side_effect=ValueError('Esse ID não é um X1 entre estes perfis.')):
            data = self.client.post(f"/duelo/{duel['id']}/verificar", data={'_csrf':'csrf-test'}, headers={'Accept':'application/json'}).get_json()
        self.assertEqual(data['state'], 'invalid')
        self.assertIn('não é um X1', self.row('SELECT * FROM social_duels')['match_error'])
        self.assertIn('Corrigir o ID', data['html'])

    def test_result_does_not_attach_to_a_concurrently_replaced_id(self):
        duel = self.create_challenge(); self.login(1); self.post(f"/duelo/{duel['id']}/aceitar")
        result = {'state':'completed','match_url':'https://aomstats.io/match/43115933','winner_profile_id':'1001','loser_profile_id':'1002'}
        original = site.verify_social_duel_match
        def replaced(snapshot, fetched_result=None):
            db = site.get_db()
            db.execute("UPDATE social_duels SET match_id='43115934',status='match_pending' WHERE id=?",(duel['id'],)); db.commit()
            return original(snapshot, fetched_result)
        with patch.object(site,'fetch_aomstats_match', return_value=result), patch.object(site,'verify_social_duel_match', side_effect=replaced):
            data = self.client.post(f"/duelo/{duel['id']}/partida", data={'_csrf':'csrf-test','match_id':'43115933'}, headers={'Accept':'application/json'}).get_json()
        stored = self.row('SELECT * FROM social_duels')
        self.assertEqual(stored['status'], 'match_pending')
        self.assertIsNone(stored['winner_id'])
        self.assertEqual(data['state'], 'conflict')

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
