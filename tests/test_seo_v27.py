"""Public discovery and privacy regressions, using isolated SQLite fixtures."""
import json
import os
import unittest
from collections import Counter
from unittest.mock import patch
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
import site_seo
import test_community_v26 as community_fixtures

site = community_fixtures.site

NS = {'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}


class SeoTests(unittest.TestCase):
    def setUp(self):
        self.fixture = community_fixtures.CommunityFlows()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.env = patch.dict(os.environ, {'GOOGLE_SITE_VERIFICATION':''})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = self.fixture.client

    def page(self, path, **kwargs):
        response = self.client.get(path, **kwargs)
        return response, BeautifulSoup(response.data, 'html.parser')

    def admin_login(self):
        with self.client.session_transaction() as session:
            session['admin_id'] = 1
            session['_csrf'] = 'csrf-test'

    def test_every_sitemap_page_is_public_indexable_and_has_matching_canonical(self):
        self.fixture.completed()
        self.fixture.make_team(0,[1],'Imperadores')
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code,200)
        urls = [node.text for node in ET.fromstring(response.data).findall('s:url/s:loc',NS)]
        self.assertEqual(len(urls),len(set(urls)))
        self.assertGreater(len(urls),150)
        titles, descriptions = [], []
        for url in urls:
            with self.subTest(url=url):
                parsed = urlsplit(url)
                r, page = self.page(parsed.path+('?' + parsed.query if parsed.query else ''))
                self.assertEqual(r.status_code,200)
                self.assertEqual(len(page.select('head > title')),1)
                self.assertEqual(len(page.select('meta[name=description]')),1)
                self.assertEqual(len(page.select('link[rel=canonical]')),1)
                self.assertEqual(page.select_one('link[rel=canonical]')['href'],url)
                self.assertNotIn('noindex',r.headers.get('X-Robots-Tag',''))
                self.assertNotIn('noindex',page.select_one('meta[name=robots]')['content'])
                self.assertIsNotNone(page.select_one('h1'))
                title = page.title.get_text()
                desc = page.select_one('meta[name=description]')['content']
                self.assertGreater(len(title),10)
                self.assertTrue(40 <= len(desc) <= 175)
                titles.append(title); descriptions.append(desc)
                graphs = [json.loads(n.string) for n in page.select('script[type="application/ld+json"]')]
                self.assertEqual(len(graphs),1)
                self.assertTrue(any(n.get('url')==url for n in graphs[0]['@graph']))
        self.assertFalse([v for v,n in Counter(titles).items() if n>1])
        self.assertFalse([v for v,n in Counter(descriptions).items() if n>1])

    def test_canonical_ignores_tracking_and_host_headers_but_keeps_real_modes(self):
        r,page = self.page('/arena/equipes?utm_source=whatsapp&modo=3v3',headers={'Host':'untrusted.example'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(page.select_one('link[rel=canonical]')['href'],site.PUBLIC_BASE_URL+'/arena/equipes?modo=3v3')
        _,page = self.page('/arena/equipes?modo=2v2&v=123')
        self.assertEqual(page.select_one('link[rel=canonical]')['href'],site.PUBLIC_BASE_URL+'/arena/equipes')
        for path in ['/','/compartilhar?utm_source=whatsapp']:
            _,page = self.page(path)
            self.assertEqual(page.select_one('link[rel=canonical]')['href'],site.PUBLIC_BASE_URL+'/')

    def test_pagination_preserves_older_history_and_filter_variants_are_noindex(self):
        for _ in range(14):
            self.fixture.completed(False,ledger=False)
        pid = self.fixture.players[0]
        r,page = self.page(f'/perfil/{pid}?pagina=2&utm_source=test')
        self.assertEqual(len(page.select('#historico-perfil .arena-history-record')),2)
        self.assertEqual(page.select_one('link[rel=canonical]')['href'],site.PUBLIC_BASE_URL+f'/perfil/{pid}?pagina=2')
        self.assertNotIn('noindex',r.headers['X-Robots-Tag'])
        self.assertIn('Página 2',page.title.get_text())
        r,page = self.page(f'/perfil/{pid}?filtro=derrotas&pagina=2')
        self.assertEqual(len(page.select('#historico-perfil .arena-history-record')),2)
        self.assertEqual(r.headers['X-Robots-Tag'],'noindex, follow')
        self.assertIn('filtro=derrotas',page.select_one('link[rel=canonical]')['href'])

    def test_duel_aliases_share_the_completed_canonical_and_keep_share_images(self):
        did = self.fixture.completed()
        row = self.fixture.row('SELECT share_token FROM social_duels WHERE id=?',(did,))
        expected = site.PUBLIC_BASE_URL+'/arena/resultado/'+row['share_token']
        for path in [f'/duelo/{did}','/arena/resultado/'+row['share_token']]:
            r,page = self.page(path)
            self.assertEqual(page.select_one('link[rel=canonical]')['href'],expected)
            self.assertNotIn('noindex',r.headers['X-Robots-Tag'])
            self.assertIn('venceu',page.title.get_text())
            self.assertIsNotNone(page.select_one('meta[property="og:image"]'))
        pending = self.fixture.create_challenge()
        r,_ = self.page(f"/duelo/{pending['id']}")
        self.assertIn('noindex',r.headers['X-Robots-Tag'])

    def test_private_pages_fragments_apis_and_errors_are_not_indexable(self):
        for path in ['/entrar','/admin/login',f'/perfil/{self.fixture.players[0]}/card','/nao-existe','/health']:
            r,page = self.page(path)
            self.assertIn('noindex',r.headers.get('X-Robots-Tag',''),path)
            if page.select_one('meta[name=robots]'):
                self.assertIn('noindex',page.select_one('meta[name=robots]')['content'])
        self.fixture.login(0)
        for path in ['/meu-perfil/editar','/meu-perfil/capa','/minha-agenda','/api/notificacoes']:
            r,_ = self.page(path)
            self.assertEqual(r.status_code,200,path)
            self.assertIn('noindex',r.headers['X-Robots-Tag'])
        self.admin_login()
        r,_ = self.page('/admin/seo')
        self.assertEqual(r.status_code,200)
        self.assertIn('noindex',r.headers['X-Robots-Tag'])
        self.assertEqual(self.client.get('/nao-existe').status_code,404)

    def test_sitemap_excludes_private_unfinished_removed_and_duplicate_urls(self):
        pending = self.fixture.create_challenge()
        self.fixture.completed()
        self.fixture.execute('UPDATE players SET is_active=0 WHERE id=?',(self.fixture.players[-1],))
        self.fixture.execute("UPDATE tournaments SET is_public=0 WHERE id=(SELECT MIN(id) FROM tournaments)")
        xml = self.client.get('/sitemap.xml').get_data(as_text=True)
        urls = [n.text for n in ET.fromstring(xml).findall('s:url/s:loc',NS)]
        self.assertNotIn(site.PUBLIC_BASE_URL+'/perfil/'+str(self.fixture.players[-1]),urls)
        for url in urls:
            self.assertFalse(any(part in url for part in ['/admin','/entrar','/meu-perfil','/minha-agenda','/card','utm_','/duelo/'+str(pending['id'])]))
        private = self.fixture.row('SELECT slug FROM tournaments WHERE is_public=0 LIMIT 1')
        self.assertNotIn('/torneio/'+private['slug'],xml)
        self.assertIn('/arena/equipes?modo=3v3',xml)
        self.assertIn('/rivalidade/',xml)

    def test_rivalry_reverse_view_points_to_one_canonical(self):
        self.fixture.completed()
        a,b = self.fixture.players[:2]
        for path in [f'/rivalidade/{a}/{b}',f'/rivalidade/{b}/{a}']:
            _,page = self.page(path)
            self.assertEqual(page.select_one('link[rel=canonical]')['href'],site.PUBLIC_BASE_URL+f'/rivalidade/{min(a,b)}/{max(a,b)}')

    def test_verification_requires_admin_and_csrf_then_appears_in_home_html(self):
        before = self.client.post('/admin/seo',data={'verification':'malicious_token_123'})
        self.assertEqual(before.status_code,302)
        self.admin_login()
        self.assertEqual(self.client.post('/admin/seo',data={'verification':'missing_csrf_123'}).status_code,400)
        token = 'google_verification_0123456789'
        r = self.client.post('/admin/seo',data={'_csrf':'csrf-test','verification':f'<meta name="google-site-verification" content="{token}" />'})
        self.assertEqual(r.status_code,302)
        _,page = self.page('/')
        self.assertEqual(page.select_one('meta[name="google-site-verification"]')['content'],token)
        self.assertIn('Chamas Flamejantes',page.title.get_text())
        self.client.post('/admin/seo',data={'_csrf':'csrf-test','verification':'<script>alert(1)</script>'})
        _,page = self.page('/')
        self.assertEqual(page.select_one('meta[name="google-site-verification"]')['content'],token)

    def test_environment_verification_and_structured_data_escape_untrusted_names(self):
        with patch.dict(os.environ,{'GOOGLE_SITE_VERIFICATION':'env_verification_012345'}):
            _,page = self.page('/')
            self.assertEqual(page.select_one('meta[name="google-site-verification"]')['content'],'env_verification_012345')
        self.fixture.execute('UPDATE players SET nickname=? WHERE id=?',('Nome </title><script>alert(1)</script> & teste',self.fixture.players[0]))
        _,page = self.page(f'/perfil/{self.fixture.players[0]}')
        self.assertEqual(len(page.select('title')),1)
        self.assertFalse([n for n in page.select('script') if n.string and n.string.strip()=='alert(1)'])
        for node in page.select('script[type="application/ld+json"]'):
            self.assertIn('@graph',json.loads(node.string))

    def test_sitemap_splits_at_protocol_limit_and_does_not_invent_dates(self):
        with patch.object(site_seo,'SITEMAP_LIMIT',10):
            root = ET.fromstring(self.client.get('/sitemap.xml').data)
            self.assertTrue(root.tag.endswith('sitemapindex'))
            pages = root.findall('s:sitemap/s:loc',NS)
            self.assertGreater(len(pages),1)
            first = ET.fromstring(self.client.get(urlsplit(pages[0].text).path).data)
            self.assertEqual(len(first.findall('s:url',NS)),10)
            self.assertEqual(self.client.get('/sitemaps/0.xml').status_code,404)
        self.assertIsNone(site_seo.modified('not-a-date'))
        self.assertIsNone(site_seo.modified('2999-01-01'))
        self.assertEqual(site_seo.modified('2020-01-01 12:00:00'),'2020-01-01T12:00:00+00:00')

    def test_robots_and_directory_allow_content_and_assets_to_be_discovered(self):
        rules = RobotFileParser()
        rules.parse(self.client.get('/robots.txt').get_data(as_text=True).splitlines())
        for path in ['/','/conhecimento','/favicon.png','/static/social.css','/entrar','/capa-chamas-flamejantes.jpg']:
            self.assertTrue(rules.can_fetch('Googlebot',path),path)
        self.assertFalse(rules.can_fetch('Googlebot','/api/notificacoes'))
        self.assertFalse(rules.can_fetch('Googlebot','/auth/google/callback'))
        _,page = self.page('/mapa-do-site')
        for build in site.knowledge_catalog()['builds']:
            with site.app.test_request_context():
                path = site.url_for('knowledge_build_page',god_slug=site.knowledge_god_slug(build['god']),build_id=build['id'])
            self.assertIsNotNone(page.select_one(f'a[href="{path}"]'))
        r,page = self.page('/conhecimento/guia-de-teclas')
        self.assertIsNotNone(page.select_one('h1'))
        self.assertIsNotNone(page.select_one('iframe'))


if __name__ == '__main__':
    unittest.main()
