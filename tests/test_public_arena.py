"""Public histories, permissions and social image delivery, using an isolated database."""
import io
import json
import unittest
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from unittest.mock import patch

from bs4 import BeautifulSoup
from PIL import Image
import test_v22_flows as fixtures

site = fixtures.site


class PublicArenaTests(unittest.TestCase):
    setUp = fixtures.SiteFlows.setUp
    login = fixtures.SiteFlows.login
    post = fixtures.SiteFlows.post
    row = fixtures.SiteFlows.row
    create_challenge = fixtures.SiteFlows.create_challenge

    def insert_duel(self, status, challenger=0, challenged=1, winner=None, match_id=''):
        with site.app.app_context():
            db=site.get_db()
            token=f'fixture-{db.execute("SELECT COUNT(*) FROM social_duels").fetchone()[0]}'
            loser = challenged if winner == challenger else challenger
            cursor=db.execute("""INSERT INTO social_duels(challenger_id,challenged_id,status,share_token,
                winner_id,loser_id,match_id,match_url) VALUES(?,?,?,?,?,?,?,?)""",(
                self.players[challenger],self.players[challenged],status,token,
                self.players[winner] if winner is not None else None,
                self.players[loser] if winner is not None else None,
                match_id, f'https://aomstats.io/match/{match_id}' if match_id else ''))
            db.commit()
            return self.row('SELECT * FROM social_duels WHERE id=?',(cursor.lastrowid,))

    def test_visitors_can_see_active_challenges_and_ids_but_cannot_change_them(self):
        duel=self.create_challenge(); self.login(1)
        self.post(f"/duelo/{duel['id']}/aceitar")
        with patch.object(site,'fetch_aomstats_match',return_value={'state':'missing','message':'Aguardando resultado','match_url':'https://aomstats.io/match/43115933'}):
            self.post(f"/duelo/{duel['id']}/partida",match_id='43115933')
        visitor=site.app.test_client()
        paths=[f"/duelo/{duel['id']}",f"/arena/desafio/{duel['share_token']}",'/x1',
               f'/perfil/{self.players[0]}',f'/perfil/{self.players[0]}/card','/x1/historico']
        for path in paths:
            with self.subTest(path=path):
                response=visitor.get(path)
                self.assertEqual(response.status_code,200)
                self.assertIn('43115933',response.get_data(as_text=True))
                soup=BeautifulSoup(response.data,'html.parser')
                self.assertIsNone(soup.select_one('form[data-match-lookup]'))
                self.assertNotIn('p0@example.test',response.get_data(as_text=True))
        self.login(2)
        with patch.object(site,'fetch_aomstats_match',side_effect=AssertionError('Unauthorized lookup')):
            for action in ['aceitar','recusar','cancelar','partida','verificar']:
                self.assertEqual(self.post(f"/duelo/{duel['id']}/{action}",match_id='43115934').status_code,403)
        self.assertEqual(self.row('SELECT * FROM social_duels')['match_id'],'43115933')

    def test_profile_filters_show_opponents_and_count_only_the_players_own_refusals(self):
        self.insert_duel('completed',winner=0,match_id='11111001')
        self.insert_duel('completed',challenged=2,winner=2,match_id='11111002')
        self.insert_duel('refused',challenger=1,challenged=0)
        self.insert_duel('refused',challenger=0,challenged=1)
        self.insert_duel('cancelled',challenger=2,challenged=0)
        path=f'/perfil/{self.players[0]}/card'
        soup=BeautifulSoup(self.client.get(path).data,'html.parser')
        self.assertEqual([dd.get_text() for dd in soup.select('.profile-stats-grid dd')],['2','1','1','1'])
        self.assertEqual(len(soup.select('.arena-history-record')),4)
        for category,expected,absent in [('vitorias','Vitória sobre André','Perdeu para Visitante'),
                                        ('derrotas','Perdeu para Visitante','Vitória sobre André'),
                                        ('fugas','Fugiu de André','André fugiu da batalha')]:
            response=self.client.get(path+'?filtro='+category)
            parsed=BeautifulSoup(response.data,'html.parser')
            records=parsed.select('.arena-history-record')
            self.assertEqual(len(records),1)
            self.assertIn(expected,records[0].get_text(' ',strip=True))
            self.assertNotIn(absent,records[0].get_text(' ',strip=True))
        refused=self.client.get(f"/x1/historico?jogador={self.players[0]}&filtro=fugas")
        self.assertIn('Fugiu de André',refused.get_data(as_text=True))

    def test_modal_history_is_paginated_without_losing_older_matches(self):
        for i in range(13): self.insert_duel('completed',winner=1,match_id=str(20000000+i))
        seen=set()
        for page,expected in [(1,5),(2,5),(3,3)]:
            response=self.client.get(f'/perfil/{self.players[0]}/card?filtro=derrotas&pagina={page}')
            soup=BeautifulSoup(response.data,'html.parser')
            self.assertEqual(len(soup.select('.arena-history-record')),expected)
            seen.update(node.get_text() for node in soup.select('.arena-match-id'))
            self.assertIn('13 registros',soup.get_text())
        self.assertEqual(len(seen),13)
        response=self.client.get(f'/perfil/{self.players[0]}/card?filtro=derrotas&pagina=999999999999')
        self.assertIn('página 3 de 3',response.get_data(as_text=True))

    def test_cancelled_challenges_are_absent_from_public_pages_and_images(self):
        duel=self.insert_duel('cancelled',match_id='22222222')
        for path in [f"/duelo/{duel['id']}",f"/arena/desafio/{duel['share_token']}",
                     f"/midia/arena/{duel['share_token']}.jpg",f"/midia/desafio/{duel['share_token']}.png"]:
            self.assertEqual(self.client.get(path).status_code,404)
        self.assertNotIn('22222222',self.client.get('/x1/historico').get_data(as_text=True))
        with site.app.test_request_context(): self.assertEqual(site.social_profile_stats(self.players[0])['refusals'],0)

    def assert_image(self, url):
        parsed=urlsplit(url)
        with self.client.get(parsed.path+'?'+parsed.query,headers={'User-Agent':'WhatsApp/2.26'}) as response:
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.mimetype,'image/jpeg')
            self.assertNotIn('Set-Cookie',response.headers)
            self.assertNotIn('Location',response.headers)
            self.assertIn('public',response.headers['Cache-Control'])
            self.assertLess(len(response.data),300_000)
            with Image.open(io.BytesIO(response.data)) as image: self.assertEqual(image.size,(1200,630))
            with self.client.head(parsed.path) as head:
                self.assertEqual(head.content_length,len(response.data))
            with self.client.get(parsed.path,headers={'If-None-Match':response.headers['ETag']}) as cached:
                self.assertEqual(cached.status_code,304)
            return response.data

    def test_victory_preview_contains_both_players_and_a_public_download(self):
        duel=self.insert_duel('completed',winner=0,match_id='43115933')
        response=self.client.get(f"/duelo/{duel['id']}")
        soup=BeautifulSoup(response.data,'html.parser')
        title=soup.select_one('meta[property="og:title"]')['content']
        self.assertIn('Makise_Kurisu_00 venceu André',title)
        self.assertIn('Compartilhar vitória',response.get_data(as_text=True))
        image_url=soup.select_one('meta[property="og:image"]')['content']
        self.assertEqual(soup.select_one('meta[name="twitter:image"]')['content'],image_url)
        self.assertEqual(soup.select_one('meta[property="og:image:secure_url"]')['content'],image_url)
        with patch.object(site.requests,'get',side_effect=AssertionError('Use cached local avatars or initials')):
            self.assert_image(image_url)
        download=soup.select_one('[data-card-share]')['data-card-download']
        with self.client.get(download) as image:
            self.assertIn('attachment',image.headers['Content-Disposition'])
            self.assertIn('vitoria-arena-',image.headers['Content-Disposition'])
        self.assertIn('venceu',soup.select_one('.share-whatsapp')['href'])

    def test_card_version_changes_with_status_and_match_id(self):
        duel=self.insert_duel('pending')
        def metadata():
            page=BeautifulSoup(self.client.get(f"/duelo/{duel['id']}").data,'html.parser')
            return page.select_one('meta[property="og:image"]')['content']
        initial=metadata()
        self.assert_image(initial)
        with site.app.app_context():
            site.get_db().execute("UPDATE social_duels SET status='match_pending',match_id='88888888' WHERE id=?",(duel['id'],));site.get_db().commit()
        pending=metadata()
        self.assertNotEqual(initial,pending)
        self.assert_image(pending)
        rules=RobotFileParser();rules.parse(self.client.get('/robots.txt').get_data(as_text=True).splitlines())
        self.assertTrue(rules.can_fetch('WhatsApp',f"/duelo/{duel['id']}"))
        self.assertTrue(rules.can_fetch('facebookexternalhit',f"/arena/desafio/{duel['share_token']}"))

    def test_all_seven_tournament_modes_have_distinct_public_artwork(self):
        import hashlib
        hashes=set()
        for mode,config in site.TOURNAMENT_TEMPLATES.items():
            with self.subTest(mode=mode):
                with site.app.app_context():
                    site.get_db().execute("""UPDATE tournaments SET name=?,mode_key=?,description=?,format_type=?,
                        team_size=?,best_of=?,max_entries=? WHERE id=?""",('Copa Chamas Flamejantes',mode,config['description'],
                        config['format_type'],config['team_size'],config['best_of'],config['max_entries'],self.tid));site.get_db().commit()
                page=BeautifulSoup(self.client.get('/torneio/teste').data,'html.parser')
                self.assertIn(config['short'],page.select_one('meta[property="og:title"]')['content'])
                self.assertIsNotNone(page.select_one('a[href="#compartilhar-torneio"]'))
                image_url=page.select_one('meta[property="og:image"]')['content']
                self.assertEqual(page.select_one('meta[name="twitter:image"]')['content'],image_url)
                hashes.add(hashlib.sha256(self.assert_image(image_url)).hexdigest())
                listing=self.client.get('/torneios').get_data(as_text=True)
                self.assertIn('COMPARTILHAR TORNEIO',listing)
                self.assertIn('https://wa.me/',listing)
        self.assertEqual(len(hashes),7)

    def test_running_tournament_is_shareable_but_private_artwork_is_not(self):
        with site.app.app_context():
            site.get_db().execute("UPDATE tournaments SET status='andamento' WHERE id=?",(self.tid,));site.get_db().commit()
        page=BeautifulSoup(self.client.get('/torneio/teste').data,'html.parser')
        self.assertIn('em andamento',page.select_one('meta[property="og:description"]')['content'])
        self.assertIsNotNone(page.select_one('.share-whatsapp'))
        with site.app.app_context():
            site.get_db().execute("UPDATE tournaments SET is_public=0 WHERE id=?",(self.tid,));site.get_db().commit()
        with self.client.session_transaction() as session: session['admin_id']=1
        self.assertEqual(self.client.get('/midia/torneio/teste.jpg').status_code,404)


if __name__=='__main__': unittest.main()
