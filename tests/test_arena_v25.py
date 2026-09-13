"""V25 regression: audited scores, durable quotas and active-only notifications."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import test_v22_flows as fixtures
import test_arena_v24 as teams
import arena_rules as rules
import arena_seasons as seasons
import arena_teams

site = fixtures.site


class ArenaRulesTests(unittest.TestCase):
    setUp = fixtures.SiteFlows.setUp
    login = fixtures.SiteFlows.login
    post = fixtures.SiteFlows.post
    row = fixtures.SiteFlows.row
    create_challenge = fixtures.SiteFlows.create_challenge

    def ratings(self, a, b):
        with site.app.app_context():
            db = site.get_db()
            db.executemany('UPDATE players SET elo_1v1=? WHERE id=?', zip([a,b],self.players[:2]))
            db.commit()

    def finish(self, duel, winner=0):
        self.login(1); self.post(f"/duelo/{duel['id']}/aceitar")
        result = dict(state='completed',match_url='https://aomstats.io/match/99115933',
                      winner_profile_id=str(1001+winner),loser_profile_id=str(1002-winner))
        with patch.object(site,'fetch_aomstats_match',return_value=result):
            return self.post(f"/duelo/{duel['id']}/partida",match_id='99115933')

    def test_bonus_boundaries_and_expected_winner(self):
        for gap, expected in [(0,(30,-20)),(99,(30,-20)),(100,(30,-20)),
                              (101,(90,-90)),(199,(90,-90)),(200,(120,-120)),
                              (299,(120,-120)),(300,(150,-150)),(400,(180,-180))]:
            with self.subTest(gap=gap):
                self.assertEqual(rules.outcome_points(1000,1000+gap),expected)
                self.assertEqual(rules.outcome_points(1000+gap,1000),(30,-20))
        self.assertEqual(rules.outcome_points(None,1800),(30,-20))
        self.assertEqual(rules.outcome_points(0,1200),(30,-20))

    def test_six_wins_four_losses_are_100_regardless_of_order(self):
        for order in [[True]*6+[False]*4,[False]*4+[True]*6,[True,False]*4+[True]*2]:
            with site.app.app_context():
                db=site.get_db(); db.execute('DELETE FROM arena_results'); db.execute('DELETE FROM arena_standings')
                a,b=self.players[:2]
                for event,won in enumerate(order):
                    seasons.record_result(db,'x1',event,[a if won else b],[b if won else a])
                rank=db.execute('SELECT * FROM arena_standings WHERE player_id=?',(a,)).fetchone()
                self.assertEqual((rank['points'],rank['score_balance'],rank['wins'],rank['losses']),(100,100,6,4))
                self.assertEqual(db.execute('SELECT SUM(points_delta) FROM arena_results WHERE player_id=?',(a,)).fetchone()[0],100)
                db.commit()

    def test_snapshot_bonus_is_immutable_and_history_keeps_statement(self):
        self.ratings(1000,1200); duel=self.create_challenge()
        self.assertEqual((duel['rating_a'],duel['rating_b']),(1000,1200))
        self.ratings(2000,2100); self.finish(duel)
        winner=self.row('SELECT * FROM arena_results WHERE won=1')
        loser=self.row('SELECT * FROM arena_results WHERE won=0')
        self.assertEqual((winner['points_delta'],loser['points_delta']),(120,-120))
        self.assertEqual((winner['rating_self'],winner['rating_opponent']),(1000,1200))
        page=self.client.get(f"/duelo/{duel['id']}").get_data(as_text=True)
        self.assertIn('+120 pts',page); self.assertIn('-120 pts',page)
        self.assertIn('+120 pontos nesta partida',self.client.get(f'/perfil/{self.players[0]}').get_data(as_text=True))

    def test_higher_elo_winning_uses_base_points(self):
        self.ratings(1200,1000); duel=self.create_challenge(); self.finish(duel)
        self.assertEqual(self.row('SELECT points_delta FROM arena_results WHERE won=1')['points_delta'],30)
        self.assertEqual(self.row('SELECT points_delta FROM arena_results WHERE won=0')['points_delta'],-20)

    def test_1300_boundary_unknown_and_reverse_direction(self):
        for a,b,allowed in [(1299,1000,True),(1300,1000,False),(1300,800,False),
                            (1000,1300,False),(1300,1001,True),(1300,None,False)]:
            with self.subTest(a=a,b=b):
                self.ratings(a,b)
                self.login(0); response=self.post(f'/perfil/{self.players[1]}/desafiar')
                duel=self.row('SELECT * FROM social_duels')
                self.assertEqual(duel is not None,allowed)
                if duel: self.post(f"/duelo/{duel['id']}/cancelar")
                with site.app.app_context():
                    site.get_db().execute('DELETE FROM arena_challenge_attempts');site.get_db().commit()
                self.assertEqual(response.status_code,302)

    def test_three_challenges_shared_between_directions_cancellation_keeps_quota(self):
        for sender in [0,1,0]:
            self.login(sender); self.post(f'/perfil/{self.players[1-sender]}/desafiar')
            duel=self.row('SELECT * FROM social_duels'); self.assertIsNotNone(duel)
            self.post(f"/duelo/{duel['id']}/cancelar")
        self.login(1); response=self.post(f'/perfil/{self.players[0]}/desafiar')
        self.assertIsNone(self.row('SELECT * FROM social_duels'))
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_challenge_attempts')['n'],3)
        self.assertIn('Limite de 3 desafios',self.client.get(response.location).get_data(as_text=True))
        for a,b in [(0,1),(1,0)]:
            self.login(a)
            modal=BeautifulSoup(self.client.get(f'/perfil/{self.players[b]}/card').data,'html.parser')
            self.assertIsNone(modal.select_one('.profile-challenge-form'))
        with patch.object(rules,'local_day',return_value='2099-01-01'):
            self.post(f'/perfil/{self.players[0]}/desafiar')
        self.assertIsNotNone(self.row('SELECT * FROM social_duels'))

    def test_daily_calendar_and_cross_mode_quota(self):
        self.assertEqual(rules.local_day('2026-09-13 02:59:59'),'2026-09-12')
        self.assertEqual(rules.local_day('2026-09-13 03:00:00'),'2026-09-13')
        with site.app.app_context():
            db=site.get_db(); a,b=self.players[:2]
            for event,queue in enumerate(['x1','2v2','3v3']): rules.record_attempt(db,queue,event,[a],[b])
            self.assertFalse(rules.challenge_check(db,[b],[a])['allowed']);db.commit()
        self.login(0);self.post(f'/perfil/{self.players[1]}/desafiar')
        self.assertIsNone(self.row('SELECT * FROM social_duels'))

    def test_concurrent_last_slot_is_not_double_spent(self):
        with site.app.app_context():
            db=site.get_db()
            for event in [-1,-2]: rules.record_attempt(db,'x1',event,[self.players[0]],[self.players[1]])
            db.commit()
        def send(_):
            client=site.app.test_client()
            with client.session_transaction() as session:
                session['social_account_id']=self.accounts[0];session['_csrf']='csrf-test'
            return client.post(f'/perfil/{self.players[1]}/desafiar',data={'_csrf':'csrf-test'}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(send,range(2))),[302,302])
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_challenge_attempts')['n'],3)
        self.assertEqual(self.row('SELECT COUNT(*) n FROM social_duels')['n'],1)

    def test_completion_removes_all_notifications_and_unread_but_keeps_profile(self):
        duel=self.create_challenge();self.login(1)
        before=self.client.get('/api/notificacoes').get_json()
        self.assertEqual(before['unread'],1)
        self.finish(duel)
        for who in [0,1]:
            self.login(who)
            feed=self.client.get('/api/notificacoes?cursor='+before['cursor']).get_json()
            self.assertEqual(feed['unread'],0)
            self.assertNotIn('notification-bubble-head',feed['html'])
            self.assertNotIn('Vitória confirmada',feed['html'])
            full=self.client.get('/notificacoes').get_data(as_text=True)
            self.assertNotIn('Vitória confirmada',full)
        self.assertEqual(self.row('SELECT status FROM social_duels')['status'],'completed')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results')['n'],2)
        self.assertIn('PARTIDA #99115933',self.client.get(f'/perfil/{self.players[0]}/card').get_data(as_text=True))
        self.assertIn('Resultado confirmado',self.client.get(f"/duelo/{duel['id']}").get_data(as_text=True))

    def test_existing_completed_and_refused_notifications_filtered_before_limit(self):
        self.login(1)
        with site.app.app_context():
            db=site.get_db()
            for i in range(25):
                did=db.execute('''INSERT INTO social_duels(challenger_id,challenged_id,status,share_token)
                    VALUES(?,?,?,?)''',(*self.players[:2], 'completed' if i%2 else 'refused',f'old-{i}')).lastrowid
                db.execute('''INSERT INTO social_notifications(account_id,duel_id,kind,message)
                  VALUES(?,?,'result','Mensagem antiga')''',(self.accounts[1],did))
            did=db.execute("INSERT INTO social_duels(challenger_id,challenged_id,share_token) VALUES(?,?,'active')",self.players[:2]).lastrowid
            for _ in range(14):
                db.execute("INSERT INTO social_notifications(account_id,duel_id,kind,message) VALUES(?,?,'challenge','Desafio ativo')",(self.accounts[1],did))
            db.commit()
        feed=self.client.get('/api/notificacoes').get_json()
        self.assertEqual(feed['unread'],14)
        self.assertEqual(feed['html'].count('notification-bubble-head'),12)
        self.assertNotIn('Mensagem antiga',feed['html'])
        page=self.client.get('/x1').get_data(as_text=True)
        self.assertIn('>14</b>',page)

    def test_migration_corrects_current_month_only_and_is_idempotent(self):
        now=seasons.utc_now(); stamp=now.isoformat(); current=seasons.period(now)
        with site.app.app_context():
            db=site.get_db();a,b=self.players[:2]
            for event,won in enumerate([True]*6+[False]*4):
                seasons.record_result(db,'x1',event,[a if won else b],[b if won else a],stamp)
            seasons.record_result(db,'x1',100,[a],[b],'2026-08-10 12:00:00')
            seasons.close_seasons(db,current)
            awards=[tuple(r) for r in db.execute('SELECT * FROM arena_awards')]
            db.execute('UPDATE arena_standings SET points=129,score_balance=129 WHERE player_id=? AND season=?',(a,current))
            db.execute("DELETE FROM site_meta WHERE key='arena_v25_migrated'")
            for table in ['arena_standings','arena_results','arena_awards']:db.execute(f'DROP TABLE {table}_before_v25')
            db.commit();seasons.init_arena(db);db.commit()
            corrected=db.execute('SELECT * FROM arena_standings WHERE player_id=? AND season=?',(a,current)).fetchone()
            self.assertEqual((corrected['points'],corrected['wins'],corrected['losses']),(100,6,4))
            self.assertEqual(db.execute('SELECT points FROM arena_standings_before_v25 WHERE player_id=? AND season=?',(a,current)).fetchone()[0],129)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_awards')],awards)
            before=[tuple(r) for r in db.execute('SELECT * FROM arena_results ORDER BY queue,event_id,player_id')]
            seasons.init_arena(db);db.commit()
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_results ORDER BY queue,event_id,player_id')],before)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_upgrade_from_v24_tables_fixes_the_exact_129_point_case(self):
        with site.app.app_context():
            db=site.get_db(); a,b=self.players[:2]
            for table in ['arena_standings','arena_results']:
                db.execute(f'DROP TABLE {table}')
            db.executescript((seasons.Path(seasons.__file__).parent/'arena_schema.sql').read_text())
            for table in ['social_duels','arena_team_duels']:
                for column in ['rating_a','rating_b','rating_source']:
                    db.execute(f'ALTER TABLE {table} DROP COLUMN {column}')
            for table in ['arena_standings','arena_results','arena_awards']:
                db.execute(f'DROP TABLE {table}_before_v25')
            db.execute("DELETE FROM site_meta WHERE key='arena_v25_migrated'")
            stamp=seasons.utc_now().replace(hour=12,minute=0,second=0,microsecond=0)
            season=seasons.period(stamp)
            states={p:dict(points=0,wins=0,losses=0,streak=0,bank=0) for p in (a,b)}
            for i,won in enumerate([False]+[True]*5+[False]*3+[True]):
                when=stamp.replace(minute=i).isoformat()
                winner,loser=(a,b) if won else (b,a)
                did=db.execute('''INSERT INTO social_duels(challenger_id,challenged_id,status,winner_id,loser_id,
                    match_id,match_payload,finished_at,share_token) VALUES(?,?,'completed',?,?,?,?,?,?)''',
                    (a,b,winner,loser,str(99115000+i),json.dumps({'state':'completed'}),when,f'legacy-{i}')).lastrowid
                for pid in (a,b):
                    old=states[pid];before=old['points'];victory=pid==winner
                    points=min(999,before+30) if victory else max(0,before-15)
                    old['streak']=0 if victory else old['streak']+1
                    old['bank']+=int(not victory)
                    if not victory and (old['streak']>=3 or old['bank']>=4):
                        points=min(points,max(0,(before//100)*100-1));old['streak']=old['bank']=0
                    old['points']=points;old['wins']+=int(victory);old['losses']+=int(not victory)
                    db.execute('INSERT INTO arena_results VALUES(?,?,?,?,?,?,?,?,?)',
                               ('x1',did,pid,season,int(victory),before,points,int(points//100<before//100),when))
            db.execute('INSERT INTO arena_seasons(season) VALUES(?)',(season,))
            for pid,state in states.items():
                db.execute('INSERT INTO arena_standings VALUES(?,?,?,?,?,?,?,?)',
                           (season,'x1',pid,state['points'],state['wins'],state['losses'],state['streak'],state['bank']))
            self.assertEqual(states[a]['points'],129)
            original_duels=[tuple(r) for r in db.execute('SELECT * FROM social_duels ORDER BY id')]
            db.commit();seasons.init_arena(db);db.commit()
            rank=db.execute('SELECT * FROM arena_standings WHERE player_id=?',(a,)).fetchone()
            self.assertEqual((rank['points'],rank['wins'],rank['losses']),(100,6,4))
            self.assertEqual(db.execute('SELECT points FROM arena_standings_before_v25 WHERE player_id=?',(a,)).fetchone()[0],129)
            self.assertEqual([tuple(r)[:-3] for r in db.execute('SELECT * FROM social_duels ORDER BY id')],original_duels)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


class TeamRulesTests(unittest.TestCase):
    setUp=teams.TeamFlows.setUp
    login=fixtures.SiteFlows.login
    post=fixtures.SiteFlows.post
    row=fixtures.SiteFlows.row
    make_team=teams.TeamFlows.make_team
    make_duel=teams.TeamFlows.make_duel
    result=teams.TeamFlows.result

    def test_team_average_bonus_and_completed_notification_cleanup(self):
        with site.app.app_context():
            db=site.get_db()
            db.executemany('UPDATE players SET elo_team=? WHERE id=?',zip([1000,1000,1200,1200],self.players[:4]));db.commit()
        duel=self.make_duel()
        with patch.object(arena_teams,'lookup_match',return_value=self.result()):
            self.post(f"/arena/equipes/duelo/{duel['id']}/partida",match_id='99115933')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results WHERE points_delta=120')['n'],2)
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_results WHERE points_delta=-120')['n'],2)
        for who in range(4):
            self.login(who); feed=self.client.get('/api/notificacoes').get_json()
            self.assertNotIn('Resultado confirmado:',feed['html'])
            self.assertNotIn(f"/arena/equipes/duelo/{duel['id']}",feed['html'])
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_duel_members')['n'],4)

    def test_team_average_cannot_hide_forbidden_opponents(self):
        with site.app.app_context():
            db=site.get_db()
            db.executemany('UPDATE players SET elo_team=? WHERE id=?',zip([1500,800,1200,1300],self.players[:4]));db.commit()
        a=self.make_team(0,[1],'A');b=self.make_team(2,[3],'B');self.login(0)
        self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        self.assertIsNone(self.row('SELECT * FROM arena_team_duels'))

    def test_x1_quota_blocks_same_opponent_in_a_new_team(self):
        with site.app.app_context():
            db=site.get_db()
            for event in range(3): rules.record_attempt(db,'x1',event,[self.players[0]],[self.players[2]])
            db.commit()
        a=self.make_team(0,[1],'A');b=self.make_team(2,[3],'B');self.login(0)
        self.post(f'/arena/equipe/{b}/desafiar',team_id=a)
        self.assertIsNone(self.row('SELECT * FROM arena_team_duels'))
