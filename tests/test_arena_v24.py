"""Season boundaries, anti-duplicate scoring, team consent and public sharing."""
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
from PIL import Image
import test_v22_flows as fixtures
import arena_seasons as seasons
import arena_teams
import aomstats_matches

site=fixtures.site

class SeasonTests(unittest.TestCase):
    setUp=fixtures.SiteFlows.setUp
    row=fixtures.SiteFlows.row

    def play(self,db,event,win=True,when='2026-09-10 12:00:00'):
        a,b=self.players[:2]
        seasons.record_result(db,'x1',event,[a if win else b],[b if win else a],when)

    def test_brasilia_month_boundary_and_archived_reward_are_idempotent(self):
        self.assertEqual(seasons.period('2026-09-01 02:59:59'),'2026-08')
        self.assertEqual(seasons.period('2026-09-01 03:00:00'),'2026-09')
        with site.app.app_context():
            db=site.get_db()
            self.play(db,1,when='2026-09-01 02:59:59')
            self.play(db,2,when='2026-09-01 03:00:00')
            seasons.close_seasons(db,'2026-09'); seasons.close_seasons(db,'2026-09')
            seasons.record_result(db,'x1',1,[self.players[0]],[self.players[1]],'2026-09-01 02:59:59')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_awards').fetchone()[0],2)
            self.assertEqual(db.execute("SELECT points FROM arena_standings WHERE player_id=? AND season='2026-09'",(self.players[0],)).fetchone()[0],30)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_results').fetchone()[0],4)

    def test_three_consecutive_losses_force_one_tier_and_reset_counters(self):
        with site.app.app_context():
            db=site.get_db()
            for i in range(6): self.play(db,i)
            for i in range(6,9): self.play(db,i,False)
            row=db.execute('SELECT * FROM arena_standings WHERE player_id=?',(self.players[0],)).fetchone()
            self.assertEqual((row['points'],row['loss_streak'],row['loss_bank']),(120,0,0))
            self.assertEqual(row['emblem_points'],99)
            self.assertEqual((row['wins'],row['losses']),(6,3))

    def test_four_losses_with_wins_between_still_demote(self):
        with site.app.app_context():
            db=site.get_db()
            for i in range(8): self.play(db,i)
            for i,win in enumerate([False,True,False,True,False,True,False],8): self.play(db,i,win)
            row=db.execute('SELECT * FROM arena_standings WHERE player_id=?',(self.players[0],)).fetchone()
            self.assertEqual(row['points'],250)
            self.assertEqual(row['emblem_points'],199)
            self.assertEqual(row['loss_bank'],0)

    def test_natural_and_forced_demotions_do_not_stack(self):
        with site.app.app_context():
            db=site.get_db()
            for i in range(8): self.play(db,i)
            for i in range(8,11): self.play(db,i,False)
            self.assertEqual(db.execute('SELECT points FROM arena_standings WHERE player_id=?',(self.players[0],)).fetchone()[0],180)

    def test_score_floor_no_ceiling_and_ten_distinct_badges(self):
        with site.app.app_context():
            db=site.get_db()
            for i in range(40): self.play(db,i)
            rows=db.execute('SELECT points FROM arena_standings ORDER BY player_id').fetchall()
            self.assertEqual([r[0] for r in rows],[1200,0])
        self.assertEqual(len({seasons.badge(i*100)['name'] for i in range(10)}),10)

    def test_monthly_ranking_excludes_historical_wins_and_modes_are_separate(self):
        with site.app.test_request_context():
            db=site.get_db()
            self.play(db,1,when='2026-08-10 12:00:00')
            seasons.record_result(db,'2v2',1,[self.players[0]],[self.players[1]],seasons.utc_now().isoformat())
            db.commit()
            x1=site.duel_ranking()
            self.assertTrue(all(p['rank']['points']==0 for p in x1))
            self.assertEqual(site.duel_ranking('2v2')[0]['rank']['points'],30)

    def test_duplicate_result_never_scores_twice(self):
        with site.app.app_context():
            db=site.get_db()
            for _ in range(3): self.play(db,5)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_results').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT MAX(points) FROM arena_standings').fetchone()[0],30)

    def test_migration_keeps_old_duels_and_imports_verified_results_once(self):
        with site.app.app_context():
            db=site.get_db()
            db.execute("DELETE FROM site_meta WHERE key='arena_v24_imported'")
            db.execute("""INSERT INTO social_duels(challenger_id,challenged_id,status,winner_id,loser_id,match_id,
                finished_at,match_payload,share_token) VALUES(?,?,'completed',?,?,'99115933','2026-09-10 10:00:00',?,'old-match')""",
                (*self.players[:2],*self.players[:2],json.dumps({'state':'completed'})))
            db.commit()
            seasons.init_arena(db); db.commit(); seasons.init_arena(db); db.commit()
            self.assertEqual(db.execute('SELECT COUNT(*) FROM social_duels').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_results').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT MAX(points) FROM arena_standings').fetchone()[0],30)

class TeamFlows(unittest.TestCase):
    login=fixtures.SiteFlows.login
    post=fixtures.SiteFlows.post
    row=fixtures.SiteFlows.row
    create_challenge=fixtures.SiteFlows.create_challenge

    def setUp(self):
        fixtures.SiteFlows.setUp(self)
        with site.app.app_context():
            db=site.get_db()
            for i in range(3,6):
                pid=db.execute('INSERT INTO players(nickname,aomstats_profile_id,aomstats_url) VALUES(?,?,?)',
                    (f'Jogador {i+1}',str(1001+i),f'https://aomstats.io/profile/{1001+i}')).lastrowid
                aid=db.execute('INSERT INTO social_accounts(google_sub,email,player_id) VALUES(?,?,?)',
                    (f'google-{i}',f'p{i}@example.test',pid)).lastrowid
                self.players.append(pid); self.accounts.append(aid)
            db.commit()

    def make_team(self,captain,partners,name,accept=True):
        self.login(captain)
        response=self.post('/arena/equipes/criar',name=name,size=len(partners)+1,members=[str(self.players[i]) for i in partners])
        self.assertEqual(response.status_code,302)
        tid=self.row('SELECT MAX(id) id FROM arena_teams')['id']
        if accept:
            for index in partners:
                self.login(index); self.post(f'/arena/equipe/{tid}/responder',answer='accept')
        return tid

    def make_duel(self,size=2):
        a=self.make_team(0,list(range(1,size)),'Chamas')
        b=self.make_team(size,list(range(size+1,2*size)),'Guardiões')
        self.login(0); self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        data=self.row('SELECT * FROM arena_team_duels ORDER BY id DESC LIMIT 1')
        self.assertIsNotNone(data)
        self.login(size); self.post(f"/arena/equipes/duelo/{data['id']}/responder",answer='accept')
        return data

    def result(self,size=2):
        return dict(state='completed',match_url='https://aomstats.io/profile/1001?leaderboard=0',match_id='99115933',
            winner_profile_ids=[str(1001+i) for i in range(size)],loser_profile_ids=[str(1001+i) for i in range(size,2*size)],
            map='Mirage',duration=368)

    def test_public_pages_and_floating_challenges_preserve_roster_and_ranking(self):
        self.create_challenge()
        with self.client.session_transaction() as session: session.clear()
        page=BeautifulSoup(self.client.get('/x1').data,'html.parser')
        floating=page.select_one('details.community-float')
        self.assertIsNotNone(floating); self.assertFalse(floating.has_attr('open'))
        self.assertIsNotNone(page.select_one('.arena-community-layout .arena-players-panel'))
        self.assertIsNotNone(page.select_one('.arena-community-layout .monthly-ranking'))
        for url in ['/arena/equipes','/arena/equipes?modo=3v3','/arena/equipes/historico','/arena/temporadas']:
            with self.subTest(url=url): self.assertEqual(self.client.get(url).status_code,200)

    def test_team_requires_each_partner_consent_and_notification_is_actionable(self):
        tid=self.make_team(0,[1,2],'Chamas',False)
        self.login(1)
        feed=self.client.get('/api/notificacoes').get_json()
        self.assertIn('ACEITAR CONVITE',feed['html'])
        self.assertIn(f'/arena/equipe/{tid}/responder',feed['html'])
        self.post(f'/arena/equipe/{tid}/responder',answer='accept')
        self.assertEqual(self.row("SELECT COUNT(*) n FROM arena_team_members WHERE team_id=? AND state='accepted'",(tid,))['n'],2)
        self.assertIn('Aguardando os convites',self.client.get(f'/arena/equipe/{tid}').get_data(as_text=True))
        self.login(2); self.post(f'/arena/equipe/{tid}/responder',answer='accept')
        self.assertIn('Pronta para a batalha',self.client.get(f'/arena/equipe/{tid}').get_data(as_text=True))

    def test_duplicate_self_or_unlinked_roster_is_rejected(self):
        self.login()
        for partners in [[self.players[0]],[self.players[1],self.players[1]],[99999]]:
            self.post('/arena/equipes/criar',name='Inválida',size=len(partners)+1,members=partners)
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_teams')['n'],0)
        self.make_team(0,[1],'Válida')
        self.login(1); self.post('/arena/equipes/criar',name='Duplicada',size=2,members=[self.players[2]])
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_teams')['n'],1)

    def test_invite_refusal_then_replacement_and_no_captain_overwrite(self):
        tid=self.make_team(0,[1],'Chamas',False)
        self.login(1); self.post(f'/arena/equipe/{tid}/responder',answer='decline')
        self.login(0); self.post(f'/arena/equipe/{tid}/convidar',player_id=self.players[0])
        self.assertEqual(self.row('SELECT state FROM arena_team_members WHERE team_id=? AND player_id=?',(tid,self.players[0]))['state'],'accepted')
        self.post(f'/arena/equipe/{tid}/convidar',player_id=self.players[2])
        self.login(2); self.post(f'/arena/equipe/{tid}/responder',answer='accept')
        self.assertIn('Pronta para a batalha',self.client.get(f'/arena/equipe/{tid}').get_data(as_text=True))

    def test_only_captains_challenge_equal_size_ready_teams(self):
        a=self.make_team(0,[1],'Dupla')
        b=self.make_team(2,[3,4],'Trio')
        self.login(1)
        self.assertEqual(self.post(f'/arena/equipe/{b}/desafiar',team_id=a).status_code,403)
        self.login(0); self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_team_duels')['n'],0)

    def test_duo_result_updates_every_player_once_and_is_public(self):
        data=self.make_duel()
        self.login(1)  # Any confirmed member can submit, not just captains.
        with patch.object(arena_teams,'lookup_match',return_value=self.result()) as fetch:
            self.post(f"/arena/equipes/duelo/{data['id']}/partida",match_id='99115933')
            self.post(f"/arena/equipes/duelo/{data['id']}/partida",match_id='99115933')
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(self.row('SELECT status FROM arena_team_duels')['status'],'completed')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results')['n'],4)
        self.assertEqual(self.row("SELECT COUNT(*) n FROM arena_standings WHERE points=30")['n'],2)
        self.assertEqual(self.row("SELECT COUNT(*) n FROM arena_standings WHERE losses=1")['n'],2)
        with self.client.session_transaction() as session: session.clear()
        page=BeautifulSoup(self.client.get(f"/arena/equipes/duelo/{data['id']}").data,'html.parser')
        self.assertIn('#99115933',page.get_text())
        self.assertNotIn('data-team-match',str(page))
        self.assertIn('Chamas venceu',page.select_one('meta[property="og:title"]')['content'])
        with self.client.get(f"/midia/equipes/{data['share_token']}.jpg?download=1") as card:
            self.assertEqual(card.status_code,200)
            self.assertIn('attachment',card.headers['Content-Disposition'])
            self.assertNotIn('Set-Cookie',card.headers)
            self.assertLess(len(card.data),300000)
            with Image.open(io.BytesIO(card.data)) as art: self.assertEqual(art.size,(1200,630))
        history=self.client.get(f'/arena/equipes/historico?jogador={self.players[1]}').get_data(as_text=True)
        self.assertIn('Chamas × Guardiões',history)
        profile=self.client.get(f'/perfil/{self.players[1]}/card').get_data(as_text=True)
        self.assertIn('1 partidas · 1 vitórias · 0 derrotas',profile)

    def test_trio_membership_result_and_six_profile_validation(self):
        data=self.make_duel(3)
        self.login(0)
        with patch.object(arena_teams,'lookup_match',return_value=self.result(3)) as lookup:
            self.post(f"/arena/equipes/duelo/{data['id']}/partida",match_id='99115933')
        self.assertEqual(lookup.call_args.kwargs['expected_teams'],[{'1001','1002','1003'},{'1004','1005','1006'}])
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results')['n'],6)
        self.assertEqual(self.row("SELECT COUNT(*) n FROM arena_standings WHERE queue='3v3'")['n'],6)

    def test_refusal_is_not_a_loss_and_cannot_be_changed_to_accepted(self):
        a=self.make_team(0,[1],'Equipe A')
        b=self.make_team(2,[3],'Equipe B')
        self.login(0); self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        did=self.row('SELECT id FROM arena_team_duels')['id']
        self.login(3)
        self.assertEqual(self.post(f'/arena/equipes/duelo/{did}/responder',answer='accept').status_code,403)
        self.login(2); self.post(f'/arena/equipes/duelo/{did}/responder',answer='decline')
        self.post(f'/arena/equipes/duelo/{did}/responder',answer='accept')
        self.assertEqual(self.row('SELECT status FROM arena_team_duels')['status'],'refused')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results')['n'],0)

    def test_pending_cancellation_deletes_duel_notifications_and_public_card(self):
        a=self.make_team(0,[1],'Equipe A'); b=self.make_team(2,[3],'Equipe B')
        self.login(0); self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        data=self.row('SELECT * FROM arena_team_duels')
        self.post(f"/arena/equipes/duelo/{data['id']}/responder",answer='cancel')
        self.assertIsNone(self.row('SELECT * FROM arena_team_duels'))
        self.assertEqual(self.client.get(f"/midia/equipes/{data['share_token']}.jpg").status_code,404)
        self.assertEqual(self.row("SELECT COUNT(*) n FROM social_notifications WHERE kind='team_challenge'")['n'],0)
        self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        newer=self.row('SELECT id FROM arena_team_duels')['id']
        self.assertGreater(newer,data['id'])
        self.assertEqual(self.client.get(f"/arena/equipes/duelo/{data['id']}").status_code,404)

    def test_changed_duel_during_lookup_cannot_receive_a_stale_result(self):
        data=self.make_duel(); self.login(0)
        def changed(*args,**kwargs):
            site.get_db().execute("UPDATE arena_team_duels SET match_id='99115934',status='match_pending' WHERE id=?",(data['id'],))
            site.get_db().commit()
            return self.result()
        with patch.object(arena_teams,'lookup_match',side_effect=changed):
            self.post(f"/arena/equipes/duelo/{data['id']}/partida",match_id='99115933')
        self.assertEqual(self.row('SELECT status FROM arena_team_duels')['status'],'match_pending')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results')['n'],0)

    def test_pending_team_notification_only_offers_response_to_the_captain(self):
        a=self.make_team(0,[1],'Equipe A'); b=self.make_team(2,[3],'Equipe B')
        self.login(0); self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        self.login(2)
        self.assertIn('ACEITAR DESAFIO',self.client.get('/api/notificacoes').get_json()['html'])
        self.login(3)
        self.assertNotIn('ACEITAR DESAFIO',self.client.get('/api/notificacoes').get_json()['html'])

    def test_guest_outsider_and_missing_csrf_cannot_submit(self):
        data=self.make_duel(); path=f"/arena/equipes/duelo/{data['id']}/partida"
        self.login(4); self.assertEqual(self.post(path,match_id='99115933').status_code,403)
        self.login(0); self.assertEqual(self.client.post(path,data={'match_id':'99115933'}).status_code,400)
        with self.client.session_transaction() as session: session.clear()
        self.assertEqual(self.client.post(path,data={'match_id':'99115933'}).status_code,302)

    def test_busy_roster_cannot_change_and_account_removal_preserves_history(self):
        data=self.make_duel()
        self.login(1); self.post(f"/arena/equipe/{data['team_a']}/sair")
        self.assertEqual(self.row('SELECT state FROM arena_team_members WHERE team_id=? AND player_id=?',(data['team_a'],self.players[1]))['state'],'accepted')
        with site.app.app_context():
            arena_teams.remove_player(site.get_db(),self.players[1]); site.get_db().commit()
        self.assertEqual(self.row('SELECT status FROM arena_team_duels')['status'],'cancelled')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_duel_members')['n'],4)
        self.assertEqual(self.client.get(f"/arena/equipes/duelo/{data['id']}").status_code,404)

    def test_shared_match_registry_prevents_reuse_between_x1_and_teams(self):
        data=self.make_duel()
        with site.app.app_context():
            db=site.get_db()
            db.execute("INSERT INTO social_duels(challenger_id,challenged_id,match_id,share_token) VALUES(?,?,'99115933','claimed')",tuple(self.players[4:6])); db.commit()
        self.login(0)
        with patch.object(arena_teams,'lookup_match',side_effect=AssertionError('Already claimed')):
            self.post(f"/arena/equipes/duelo/{data['id']}/partida",match_id='99115933')
        self.assertEqual(self.row('SELECT match_id FROM arena_team_duels')['match_id'],'')
        with site.app.app_context():
            with self.assertRaises(sqlite3.IntegrityError):
                site.get_db().execute("UPDATE arena_team_duels SET match_id='99115933' WHERE id=?",(data['id'],))

    def test_pending_lookup_ends_and_can_be_corrected(self):
        data=self.make_duel(); self.login(0)
        url=f"/arena/equipes/duelo/{data['id']}/partida"
        with patch.object(arena_teams,'lookup_match',return_value={'state':'unavailable','match_url':'https://aomstats.io/match/99115933','message':'Consulta encerrada.'}):
            response=self.client.post(url,data={'_csrf':'csrf-test','match_id':'99115933'},headers={'Accept':'application/json'})
        self.assertTrue(response.get_json()['refresh'])
        self.assertEqual(self.row('SELECT status FROM arena_team_duels')['status'],'match_pending')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results')['n'],0)
        with patch.object(arena_teams,'lookup_match',return_value=self.result()):
            self.post(url,match_id='99115934')
        self.assertEqual(self.row('SELECT match_id FROM arena_team_duels')['match_id'],'99115934')

class TeamParserTests(unittest.TestCase):
    def html(self,size=2,missing=False,mixed=False,extra=False):
        profiles=[]
        for i in range(size*2+int(extra)):
            result='text-stats-high' if i<size else 'text-stats-low'
            if mixed and i in (0,size): result='text-stats-low' if i==0 else 'text-stats-high'
            if missing and i==0: result=''
            profiles.append(f'<div><img alt="Zeus portrait"><a href="/profile/{1001+i}">Jogador {i}</a><svg class="{result}"></svg></div>')
        return '<article><h3>Mirage</h3><p>ID: 99115933</p>'+''.join(profiles)+'</article>'

    def lookup(self,html,size=2):
        with patch.object(aomstats_matches,'_fetch_document',return_value={'html':html}):
            return aomstats_matches.lookup_match('99115933',[str(1001+i) for i in range(size*2)],
                expected_teams=[[str(1001+i) for i in range(size)],[str(1001+i) for i in range(size,size*2)]])

    def test_duo_and_trio_outcomes(self):
        for size in (2,3):
            result=self.lookup(self.html(size),size)
            self.assertEqual(result['state'],'completed')
            self.assertEqual(len(result['winner_profile_ids']),size)

    def test_no_result_inferred_from_teammates(self):
        self.assertEqual(self.lookup(self.html(missing=True))['state'],'pending')

    def test_mixed_teams_or_extra_players_rejected(self):
        for html in [self.html(mixed=True),self.html(extra=True)]:
            with self.assertRaises(ValueError): self.lookup(html)
