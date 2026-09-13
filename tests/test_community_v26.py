"""Integration of the community with real SQLite, isolated accounts and saved results."""
import io
import json
import sqlite3
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
import test_v22_flows as fixtures
import test_arena_v24 as team_fixtures
import community_hub as hub
import duel_extras as extras

site = fixtures.site


class CommunityFlows(unittest.TestCase):
    setUp = team_fixtures.TeamFlows.setUp
    login = fixtures.SiteFlows.login
    post = fixtures.SiteFlows.post
    row = fixtures.SiteFlows.row
    create_challenge = fixtures.SiteFlows.create_challenge
    make_team = team_fixtures.TeamFlows.make_team
    make_duel = team_fixtures.TeamFlows.make_duel
    result = team_fixtures.TeamFlows.result

    def execute(self, sql, params=()):
        with site.app.app_context():
            db = site.get_db(); cursor = db.execute(sql, params); db.commit()
            return cursor.lastrowid

    def completed(self, won=True, when=None, ratings=(None, None), ledger=True):
        a, b = self.players[:2]
        winner, loser = (a, b) if won else (b, a)
        when = when or datetime.now(timezone.utc)
        with site.app.app_context():
            db = site.get_db()
            did = db.execute("""INSERT INTO social_duels(challenger_id,challenged_id,status,
                winner_id,loser_id,finished_at,share_token,rating_a,rating_b,rating_source)
                VALUES(?,?,'completed',?,?,?,?,?,?,'challenge')""",
                (a,b,winner,loser,when.isoformat(),uuid.uuid4().hex,*ratings)).lastrowid
            db.execute('UPDATE social_duels SET match_id=? WHERE id=?', (str(80000000+did),did))
            if ledger: site.arena_seasons.record_result(db,'x1',did,[winner],[loser],when)
            db.commit()
        return did

    def accepted(self):
        duel = self.create_challenge(); self.login(1)
        self.post(f"/duelo/{duel['id']}/aceitar"); self.login(0)
        return duel['id']

    def when_input(self, minutes=60):
        return (extras.now_utc()+timedelta(minutes=minutes)).astimezone(site.arena_seasons.ZONE).strftime('%Y-%m-%dT%H:%M')

    def propose(self, did, version=0, queue='x1'):
        return self.post(f'/agenda/{queue}/{did}/propor',when=self.when_input(),version=version)

    def upload(self, did, content=None, name='batalha.mythrec', queue='x1'):
        return self.post(f'/replay/{queue}/{did}/enviar',replay=(io.BytesIO(content or bytes(range(256))*8),name),description='Rever a abertura',game_version='Teste')

    def publication(self):
        self.login(0)
        response = self.post('/mural/publicar',kind='estrategia',title='Abertura de Zeus',body='Uma estratégia de treino.')
        self.assertEqual(response.status_code,302)
        return self.row('SELECT * FROM community_posts ORDER BY id DESC LIMIT 1')['id']

    def test_rivalry_keeps_complete_history_scores_last_win_and_longest_run(self):
        start = datetime.now(timezone.utc)-timedelta(days=3)
        ids = [self.completed(w, start+timedelta(minutes=i),ledger=False) for i,w in enumerate([1,1,0,0,1])]
        self.execute("INSERT INTO social_duels(challenger_id,challenged_id,status,share_token) VALUES(?,?,'refused',?)",(*self.players[:2],uuid.uuid4().hex))
        with site.app.app_context():
            a=hub.profile_rivalries(site.get_db(),self.players[0])[0]
            b=hub.profile_rivalries(site.get_db(),self.players[1])[0]
        self.assertEqual((a['wins'],a['losses'],a['best_self'],a['best_opponent']),(3,2,2,2))
        self.assertEqual((b['wins'],b['losses']),(2,3))
        self.assertEqual(a['last_self']['id'],ids[-1]);self.assertEqual(a['last_opponent']['id'],ids[3])
        self.assertEqual(len(a['history']),5)
        page=self.client.get(f'/rivalidade/{self.players[0]}/{self.players[1]}')
        self.assertEqual(page.status_code,200);self.assertIn(str(80000000+ids[-1]),page.get_data(as_text=True))

    def test_rivalry_pagination_and_inactive_opponents_keep_old_results(self):
        for i in range(27):self.completed(i%2==0,ledger=False)
        self.execute('UPDATE players SET is_active=0 WHERE id=?',(self.players[1],))
        path=f'/rivalidade/{self.players[0]}/{self.players[1]}'
        first=BeautifulSoup(self.client.get(path).data,'html.parser')
        second=BeautifulSoup(self.client.get(path+'?pagina=2').data,'html.parser')
        self.assertEqual(len(first.select('.hub-match-row')),25)
        self.assertEqual(len(second.select('.hub-match-row')),2)
        self.assertEqual(self.client.get(f'/rivalidade/{self.players[0]}/{self.players[0]}').status_code,404)

    def test_monthly_graph_uses_real_zero_floor_and_frozen_elo_bonus(self):
        start=datetime.now(timezone.utc).replace(day=5,hour=12,minute=0,second=0,microsecond=0)
        for i in range(2):self.completed(False,start+timedelta(minutes=i))
        upset=self.completed(True,start+timedelta(minutes=2),(1000,1200))
        self.execute('UPDATE players SET elo_1v1=1800 WHERE id=?',(self.players[0],))
        with site.app.app_context():
            rows=[dict(r) for r in site.get_db().execute('SELECT * FROM arena_results WHERE player_id=? ORDER BY recorded_at',(self.players[0],))]
            graph=hub.evolution(rows,'x1',site.arena_seasons.period(start))
        self.assertEqual([e['after'] for e in graph['events']],[0,0,120])
        self.assertEqual(graph['events'][0]['delta'],-30);self.assertEqual(graph['events'][0]['applied'],0)
        self.assertEqual(graph['events'][-1]['adjustment'],90);self.assertEqual(graph['events'][-1]['event_id'],upset)
        page=BeautifulSoup(self.client.get(f'/perfil/{self.players[0]}').data,'html.parser')
        plotted=json.loads(page.select_one('[data-chart-events]').string)
        self.assertEqual(plotted[-1]['after'],120);self.assertIsNotNone(page.select_one('.hub-ledger table'))

    def test_achievements_survive_season_boundaries_and_later_defeats(self):
        start=datetime.now(timezone.utc).replace(day=1,hour=0,minute=0,second=0,microsecond=0)-timedelta(days=1)
        for i in range(5):self.completed(True,start+timedelta(minutes=i),(1000,1200) if i==0 else (None,None))
        self.completed(False,datetime.now(timezone.utc))
        with site.app.app_context():
            rows=[dict(r) for r in site.get_db().execute('SELECT * FROM arena_results WHERE player_id=? ORDER BY recorded_at',(self.players[0],))]
            unlocked=hub.achievements(rows,hub.profile_rivalries(site.get_db(),self.players[0]))
        self.assertEqual([a['unlocked'] for a in unlocked],[True,True,True])
        self.assertLess(hub.as_utc(unlocked[0]['date']),datetime.now(timezone.utc).replace(day=1,hour=0,minute=0,second=0))

    def test_legacy_achievements_do_not_guess_elo_from_current_profile(self):
        for i in range(5):self.completed(True,ledger=False)
        self.execute('UPDATE players SET elo_1v1=1700 WHERE id=?',(self.players[1],))
        with site.app.app_context():
            result=hub.achievements([],hub.profile_rivalries(site.get_db(),self.players[0]))
        self.assertEqual([r['unlocked'] for r in result],[True,True,False])

    def test_covers_are_owned_validated_and_visible_in_full_profile_and_popup(self):
        self.login(0)
        page=BeautifulSoup(self.client.get('/meu-perfil/capa').data,'html.parser')
        choices=page.select('input[name="cover_key"]');self.assertGreater(len(choices),10)
        key=next(n['value'] for n in choices if n['value']!='chamas')
        self.assertEqual(self.post('/meu-perfil/capa',cover_key=key,player_id=self.players[1]).status_code,302)
        self.assertEqual(self.row('SELECT player_id FROM community_profile_settings')['player_id'],self.players[0])
        self.assertEqual(self.post('/meu-perfil/capa',cover_key='url(javascript:alert(1))').status_code,400)
        for path in [f'/perfil/{self.players[0]}',f'/perfil/{self.players[0]}/card']:
            html=self.client.get(path).get_data(as_text=True);self.assertIn(key+'.webp',html)
            self.assertIn('hub-covered',html);self.assertIn('data-aom-player',html)

    def test_build_notes_and_favorites_are_private_per_google_account(self):
        with site.app.test_request_context():
            build=site.knowledge_catalog()['builds'][0]
            path=site.url_for('knowledge_build_page',god_slug=site.knowledge_god_slug(build['god']),build_id=build['id'])
        self.login(0)
        marker='Segredo de treino <script>alert(1)</script>'
        response=self.post('/minhas-builds/'+build['id'],favorite='1',notes=marker,account_id=self.accounts[1])
        self.assertEqual(response.status_code,302)
        self.assertIn('Segredo de treino',self.client.get('/minhas-builds').get_data(as_text=True))
        self.assertNotIn('<script>alert(1)</script>',self.client.get(path).get_data(as_text=True))
        self.login(1)
        self.assertNotIn('Segredo de treino',self.client.get('/minhas-builds').get_data(as_text=True))
        self.assertNotIn('Segredo de treino',self.client.get(path).get_data(as_text=True))
        self.login(0);self.post('/minhas-builds/'+build['id'],favorite='0',notes='Somente anotação')
        self.assertIn('Somente anotação',self.client.get('/minhas-builds').get_data(as_text=True))
        self.post('/minhas-builds/'+build['id'],notes='')
        self.assertIsNone(self.row('SELECT * FROM community_build_notes'))

    def test_wall_victories_require_a_confirmed_win_and_do_not_duplicate_or_change_score(self):
        did=self.completed();self.login(1)
        self.assertEqual(self.post('/mural/publicar',kind='vitoria',event=f'x1:{did}').status_code,403)
        self.login(0)
        before=self.row('SELECT * FROM arena_results WHERE player_id=?',(self.players[0],))
        response=self.post('/mural/publicar',kind='vitoria',event=f'x1:{did}',title='Título falso')
        self.assertEqual(response.status_code,302)
        duplicate=self.post('/mural/publicar',kind='vitoria',event=f'x1:{did}')
        self.assertEqual(duplicate.location,response.location)
        self.assertEqual(self.row('SELECT COUNT(*) n FROM community_posts')['n'],1)
        self.assertEqual(self.row('SELECT * FROM arena_results WHERE player_id=?',(self.players[0],)),before)
        page=BeautifulSoup(self.client.get(response.location).data,'html.parser')
        self.assertIsNotNone(page.select_one('meta[property="og:image"]'))
        self.assertNotIn('Título falso',page.get_text());self.assertIn('venceu',page.get_text())

    def test_posts_are_escaped_and_only_owner_or_admin_can_edit_and_remove(self):
        post_id=self.publication();path=f'/mural/publicacao/{post_id}'
        self.login(1)
        for action in ['editar','excluir']:
            self.assertEqual(self.post(path+'/'+action,title='Invasão',body='Outro autor').status_code,403)
        self.login(0)
        self.assertEqual(self.post(path+'/editar',title='Nova estratégia',body='<img src=x onerror=alert(1)>').status_code,302)
        page=BeautifulSoup(self.client.get(path).data,'html.parser')
        self.assertFalse(page.select('[onerror]'));self.assertIn('<img',page.get_text())
        self.login(1)
        with self.client.session_transaction() as s:s['admin_id']=1
        self.assertEqual(self.post(path+'/excluir').status_code,302)
        self.assertEqual(self.client.get(path).status_code,404)

    def test_like_is_idempotent_and_unlike_only_changes_own_like(self):
        post_id=self.publication();path=f'/mural/publicacao/{post_id}/curtir'
        self.login(1)
        for _ in range(2):
            result=self.client.post(path,data={'_csrf':'csrf-test','liked':'1'},headers={'Accept':'application/json'})
            self.assertEqual(result.get_json(),{'liked':True,'count':1})
        self.login(2);self.post(path,liked='1');self.login(1);self.post(path,liked='0')
        self.assertEqual(self.row('SELECT player_id FROM community_likes')['player_id'],self.players[2])
        self.assertEqual(self.post(path,liked='toggle').status_code,400)

    def test_comments_notify_author_disappear_on_read_and_require_ownership_to_delete(self):
        post_id=self.publication();self.login(1)
        response=self.post(f'/comentar/post/{post_id}',body='Como melhorar o avanço?')
        self.assertEqual(response.status_code,302)
        comment=self.row('SELECT * FROM community_comments')
        self.assertIn('comentario-'+str(comment['id']),response.location)
        self.login(2);self.assertEqual(self.post(f"/comentario/{comment['id']}/excluir").status_code,403)
        self.login(0)
        feed=self.client.get('/api/notificacoes').get_json();self.assertIn('Novo comentário',feed['html'])
        self.client.get(f'/mural/publicacao/{post_id}')
        self.assertNotIn('Novo comentário',self.client.get('/api/notificacoes').get_json()['html'])
        self.login(1);self.post(f"/comentario/{comment['id']}/excluir")
        self.assertEqual(self.row('SELECT deleted FROM community_comments')['deleted'],1)

    def test_wall_and_comment_pagination_and_rate_limit(self):
        post_id=self.publication()
        with site.app.app_context():
            db=site.get_db()
            db.executemany("INSERT INTO community_comments(author_id,post_id,body,created_at) VALUES(?,?,?,'2020-01-01')",[(self.players[1],post_id,f'Análise {i}') for i in range(31)])
            db.executemany("INSERT INTO community_posts(author_id,kind,title,body,created_at) VALUES(?,'novidade',?,?,'2020-01-01')",[(self.players[1],f'Novidade {i}','Texto') for i in range(13)])
            db.commit()
        first=BeautifulSoup(self.client.get('/mural').data,'html.parser')
        self.assertEqual(len(first.select('article.hub-post')),12)
        self.login(1);response=self.post(f'/comentar/post/{post_id}',body='Comentário na última página')
        self.assertIn('pagina=2',response.location)
        self.assertIn('Comentário na última página',self.client.get(response.location).get_data(as_text=True))
        for i in range(9):self.post(f'/comentar/post/{post_id}',body=f'Pergunta {i}')
        self.assertEqual(self.post(f'/comentar/post/{post_id}',body='Limite').status_code,429)

    def test_scheduling_requires_both_sides_and_rejects_stale_versions(self):
        did=self.accepted();self.assertEqual(self.propose(did).status_code,302)
        self.assertEqual(self.post(f'/agenda/x1/{did}/responder',version=1,answer='accept').status_code,403)
        self.login(2);self.assertEqual(self.propose(did,1).status_code,403)
        self.login(1);self.assertEqual(self.post(f'/agenda/x1/{did}/responder',version=1,answer='accept').status_code,302)
        self.assertEqual(self.row('SELECT status FROM arena_schedules')['status'],'confirmed')
        self.login(0);self.assertEqual(self.propose(did,1).status_code,302)
        self.login(1);self.assertEqual(self.post(f'/agenda/x1/{did}/responder',version=1,answer='accept').status_code,409)
        self.assertEqual(self.row('SELECT status FROM arena_schedules')['status'],'proposed')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_schedule_events')['n'],3)
        self.assertEqual(self.client.get('/minha-agenda').status_code,200)

    def test_scheduling_validates_time_and_match_state_and_cancel_preserves_duel(self):
        did=self.accepted()
        for when in [self.when_input(-1),'2026-50-99T10:00','bad',self.when_input(91*24*60)]:
            self.assertEqual(self.post(f'/agenda/x1/{did}/propor',when=when,version=0).status_code,400)
        self.propose(did)
        self.assertEqual(self.post(f'/agenda/x1/{did}/responder',answer='cancel',version=1).status_code,302)
        self.assertEqual(self.row('SELECT status FROM social_duels WHERE id=?',(did,))['status'],'accepted')
        self.execute("UPDATE social_duels SET match_id='43270001',status='match_pending' WHERE id=?",(did,))
        self.assertEqual(self.propose(did,1).status_code,409)

    def test_reminders_use_brasilia_time_once_per_stage_across_connections(self):
        did=self.accepted();when=self.when_input();self.post(f'/agenda/x1/{did}/propor',when=when,version=0)
        self.login(1);self.post(f'/agenda/x1/{did}/responder',version=1,answer='accept')
        schedule=self.row('SELECT * FROM arena_schedules');at=hub.as_utc(schedule['scheduled_at'])
        self.assertEqual(at,datetime.strptime(when,'%Y-%m-%dT%H:%M').replace(tzinfo=site.arena_seasons.ZONE).astimezone(timezone.utc))
        with site.app.app_context():
            db=site.get_db();self.assertEqual(extras.process_reminders(db,at-timedelta(minutes=10)),2)
        with sqlite3.connect(site.DB_PATH) as db:
            db.row_factory=sqlite3.Row
            self.assertEqual(extras.process_reminders(db,at-timedelta(minutes=5)),0)
            self.assertEqual(extras.process_reminders(db,at),2)
            self.assertEqual(extras.process_reminders(db,at),0)
        self.assertEqual(self.row("SELECT COUNT(*) n FROM social_notifications WHERE kind='schedule_reminder'")['n'],4)
        self.execute("UPDATE social_duels SET status='completed',winner_id=?,loser_id=? WHERE id=?",(*self.players[:2],did))
        self.assertNotIn('Horário do duelo',self.client.get('/api/notificacoes').get_json()['html'])

    def test_rescheduled_duels_get_new_reminders_and_cancelled_schedules_get_none(self):
        did=self.accepted();self.propose(did);self.login(1);self.post(f'/agenda/x1/{did}/responder',version=1,answer='accept')
        at=hub.as_utc(self.row('SELECT scheduled_at FROM arena_schedules')['scheduled_at'])
        with site.app.app_context():self.assertEqual(extras.process_reminders(site.get_db(),at),2)
        self.login(0);self.propose(did,1);self.login(1);self.post(f'/agenda/x1/{did}/responder',version=2,answer='accept')
        with site.app.app_context():self.assertEqual(extras.process_reminders(site.get_db(),at),2)
        self.post(f'/agenda/x1/{did}/responder',version=2,answer='cancel')
        with site.app.app_context():self.assertEqual(extras.process_reminders(site.get_db(),at-timedelta(minutes=10)),0)

    def test_team_schedule_only_captains_control_and_every_member_is_reminded(self):
        duel=self.make_duel(3);did=duel['id'];self.login(1)
        self.assertEqual(self.propose(did,queue='3v3').status_code,403)
        self.login(0);self.assertEqual(self.propose(did,queue='3v3').status_code,302)
        self.login(3);self.post(f'/agenda/3v3/{did}/responder',version=1,answer='accept')
        at=hub.as_utc(self.row('SELECT scheduled_at FROM arena_schedules')['scheduled_at'])
        with site.app.app_context():self.assertEqual(extras.process_reminders(site.get_db(),at),6)
        self.assertEqual(self.client.get(f'/arena/equipes/duelo/{did}').status_code,200)

    def test_replay_upload_is_participant_only_and_completed_only(self):
        did=self.accepted();self.assertEqual(self.upload(did).status_code,409)
        self.login(2);self.assertEqual(self.upload(did).status_code,403)
        self.assertIsNone(self.row('SELECT * FROM arena_replays'))
        self.execute("UPDATE social_duels SET status='completed',winner_id=?,loser_id=? WHERE id=?",(*self.players[:2],did))
        self.login(0)
        self.assertEqual(self.upload(did,name='wrong.exe').status_code,400)
        self.assertEqual(self.upload(did,content=b'empty').status_code,400)
        self.assertFalse(list((site.DB_PATH.parent/'arena_replays').glob('*')))

    def test_replay_public_download_comments_and_deletion_preserve_the_result(self):
        did=self.completed();self.login(0)
        response=self.upload(did,name='../../partida.mythrec');self.assertEqual(response.status_code,302)
        replay=self.row('SELECT * FROM arena_replays');rid=replay['id']
        self.assertEqual(replay['original_name'],'partida.mythrec')
        self.assertTrue((site.DB_PATH.parent/'arena_replays'/replay['filename']).is_file())
        self.assertFalse((site.UPLOAD_DIR/replay['filename']).exists())
        anon=site.app.test_client()
        with anon.get(f'/replays/{rid}/baixar') as download:
            self.assertEqual(download.status_code,200);self.assertEqual(download.data,bytes(range(256))*8)
            self.assertIn('attachment',download.headers['Content-Disposition'])
            self.assertEqual(download.headers['X-Content-Type-Options'],'nosniff')
        self.assertEqual(anon.get(f'/replays/{rid}').status_code,200)
        self.login(1);self.post(f'/comentar/replay/{rid}',body='Boa abertura!')
        self.assertEqual(self.post(f'/replays/{rid}/excluir').status_code,403)
        self.login(0);before=self.row('SELECT * FROM arena_results WHERE player_id=?',(self.players[0],))
        self.assertEqual(self.post(f'/replays/{rid}/excluir').status_code,302)
        self.assertEqual(anon.get(f'/replays/{rid}/baixar').status_code,404)
        self.assertEqual(self.row('SELECT * FROM arena_results WHERE player_id=?',(self.players[0],)),before)
        self.assertEqual(self.row('SELECT status FROM social_duels')['status'],'completed')

    def test_duplicate_and_oversize_replays_leave_no_orphan_files(self):
        did=self.completed();self.login(0)
        original=self.upload(did);duplicate=self.upload(did)
        self.assertEqual(original.location,duplicate.location)
        self.assertEqual(self.upload(did,content=b'new'*100).status_code,409)
        self.login(1)
        with patch.object(extras,'REPLAY_MAX_BYTES',256):
            self.assertEqual(self.upload(did).status_code,413)
        self.assertEqual(len(list((site.DB_PATH.parent/'arena_replays').glob('*'))),1)
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_replays')['n'],1)

    def test_team_victory_posts_and_replays_use_confirmed_roster(self):
        import arena_teams
        duel=self.make_duel(2);did=duel['id'];self.login(0)
        with patch.object(arena_teams,'lookup_match',return_value=self.result(2)):
            result=self.post(f'/arena/equipes/duelo/{did}/partida',match_id='99115933')
        self.assertEqual(result.status_code,302)
        self.login(1)
        self.assertEqual(self.post('/mural/publicar',kind='vitoria',event=f'2v2:{did}').status_code,302)
        response=self.upload(did,queue='2v2');self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.get(response.location).status_code,200)
        self.login(2);self.assertEqual(self.post('/mural/publicar',kind='vitoria',event=f'2v2:{did}').status_code,403)
        self.login(4);self.assertEqual(self.upload(did,queue='2v2').status_code,403)

    def test_new_mutations_require_csrf_and_private_pages_require_login(self):
        did=self.completed();post_id=self.publication()
        for url in ['/meu-perfil/capa','/mural/publicar',f'/agenda/x1/{did}/propor',f'/replay/x1/{did}/enviar',f'/mural/publicacao/{post_id}/curtir',f'/comentar/post/{post_id}']:
            self.assertEqual(self.client.post(url,data={}).status_code,400,url)
        anon=site.app.test_client()
        for url in ['/meu-perfil/capa','/minhas-builds','/minha-agenda']:
            self.assertEqual(anon.get(url).status_code,302,url)

    def test_migration_is_additive_idempotent_and_full_ranking_stays_complete(self):
        self.completed();self.publication()
        with site.app.app_context():
            db=site.get_db()
            before={table:[tuple(r) for r in db.execute('SELECT * FROM '+table)] for table in ['players','social_duels','arena_results','arena_standings','community_posts']}
            for _ in range(2):hub.init_schema(db);extras.init_schema(db);db.commit()
            for table,rows in before.items():self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+table)],rows)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            for i in range(25):
                pid=db.execute('INSERT INTO players(nickname,aomstats_profile_id,aomstats_url) VALUES(?,?,?)',(f'Ranking {i}',str(7000+i),f'https://aomstats.io/profile/{7000+i}')).lastrowid
                db.execute('INSERT INTO community_members(player_id,community_elo) VALUES(?,0)',(pid,))
            db.commit()
        page=BeautifulSoup(self.client.get('/x1').data,'html.parser')
        self.assertGreater(len(page.select('.monthly-ranking-row')),25)
        self.assertFalse(page.select('button button'))
        self.assertIsNotNone(page.select_one('.monthly-ranking-row [data-copy-match]'))
