"""V28: month evidence, live result flow, historical repair and rollback."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import test_v22_flows as fixtures
import arena_rules as rules
import arena_seasons as seasons
import arena_balance as balance
import aomstats_activity as activity

site = fixtures.site


def proof(profile='1001', count=8, period=None):
    period = period or seasons.period()
    base = int(period.replace('-', '')) * 1000
    records = [dict(profile_id=profile, match_id=str(base + i), leaderboard_id=1 + i % 4,
                    completed_at=f'{period}-01T03:{i:02d}:00+00:00',
                    source_url=f'https://aomstats.io/profile/{profile}?leaderboard={1+i%4}') for i in range(count)]
    return dict(records=records, available=True)


class ActivityTests(unittest.TestCase):
    def test_special_boundaries_cap_and_unqualified_standard_formula(self):
        for gap, points in [(1,40),(99,40),(100,40),(101,50),(199,50),(200,50),(201,50),(300,50),(1000,50)]:
            with self.subTest(gap=gap):
                high, low = (1000, 1000-gap) if gap < 1000 else (1900,900)
                self.assertEqual(rules.outcome_points(low,high,8),(points,-points))
                self.assertEqual(rules.outcome_points(high,low,8),(30,-30))
                self.assertEqual(rules.outcome_points(low,high,7),rules.outcome_points(low,high))
        for low,high in [(1000,1200),(800,999),(None,1200),(0,1200)]:
            self.assertEqual(rules.outcome_points(low,high,8),rules.outcome_points(low,high))

    def test_only_unique_completed_ranked_records_count(self):
        now = datetime(2026,9,14,tzinfo=timezone.utc)
        base = dict(match_id=90000111,profile_id=123,leaderboard_id=1,
                    startgametime=1788991200,completiontime=1788992200,resulttype=1,win=True)
        rows = [base, dict(base)]
        variants = [dict(leaderboard_id=0),dict(leaderboard_id=5),dict(profile_id=456),
                    dict(completiontime=None),dict(resulttype=4),dict(win=False),
                    dict(missing_from_api=True),dict(out_of_sync=True),
                    dict(completiontime=int(now.timestamp())+1),dict(startgametime=1788992200)]
        rows.extend(dict(base, match_id=90000200+i, **change) for i,change in enumerate(variants))
        html = '<h1>999 games - 500 W 499 L</h1><script>const matches='+json.dumps(rows)+'</script>'
        parsed = activity.parse_activity(html,'123',now)
        self.assertEqual(len(parsed),1)
        self.assertEqual(parsed[0]['match_id'],'90000111')
        self.assertEqual(activity.parse_activity('<h1>999 games</h1>','123',now),[])

    def test_actual_aomstats_serialized_shape(self):
        doc = (Path(__file__).parent/'fixtures/aomstats_activity_v28.html').read_text()
        rows = activity.parse_activity(doc,'1076869557',datetime(2026,9,14,tzinfo=timezone.utc))
        self.assertEqual(len(rows),9)
        self.assertTrue(all(r['leaderboard_id']==1 for r in rows))

    def test_brasilia_month_and_failed_fetch_do_not_invent_activity(self):
        self.assertEqual(balance.month('2026-09-01T02:59:59+00:00'),'2026-08')
        self.assertEqual(balance.month('2026-09-01T03:00:00+00:00'),'2026-09')
        with patch.object(activity,'_fetch_document',return_value={'error':True}):
            self.assertEqual(activity.fetch_activity('123'),dict(records=[],available=False))


class BalanceTests(unittest.TestCase):
    setUp = fixtures.SiteFlows.setUp
    login = fixtures.SiteFlows.login
    post = fixtures.SiteFlows.post
    row = fixtures.SiteFlows.row
    create_challenge = fixtures.SiteFlows.create_challenge

    def event(self, db, event, low_wins=True, when=None, ratings=(900,1200), identity=True):
        a,b = self.players[:2]
        when = when or seasons.utc_now().isoformat()
        winner,loser = (a,b) if low_wins else (b,a)
        payload = {'state':'completed'}
        if identity:
            payload.update(winner_profile_id='1001' if low_wins else '1002',
                           loser_profile_id='1002' if low_wins else '1001')
        db.execute('''INSERT INTO social_duels
            (id,challenger_id,challenged_id,status,winner_id,loser_id,match_id,match_payload,
             requested_at,finished_at,share_token,rating_a,rating_b,rating_source)
            VALUES(?,?,?,'completed',?,?,?,?,?,?,?,?,?,'challenge')''',
            (event,a,b,winner,loser,str(90000000+event),json.dumps(payload),when,when,
             f'v28-{event}',*ratings))
        seasons.record_result(db,'x1',event,[winner],[loser],when)

    def result(self,db,event,won=1):
        return dict(db.execute('SELECT * FROM arena_results WHERE event_id=? AND won=?',(event,won)).fetchone())

    def snapshot(self,db,table):
        return [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]

    def test_seven_then_eight_repair_both_sides_and_following_balances_once(self):
        with site.app.app_context():
            db=site.get_db();when=seasons.utc_now()-timedelta(hours=1)
            for i in range(6):self.event(db,i+1,False,(when+timedelta(minutes=i)).isoformat())
            self.event(db,7,True,(when+timedelta(minutes=7)).isoformat())
            self.event(db,8,False,(when+timedelta(minutes=8)).isoformat())
            self.assertEqual(self.result(db,7)['points_delta'],150)
            duels=self.snapshot(db,'social_duels');players=self.snapshot(db,'players')
            balance.store_activity(db,'1001',proof(count=7))
            self.assertEqual(balance.reconcile(db),0)
            balance.store_activity(db,'1001',proof(count=8))
            self.assertEqual(balance.reconcile(db),1)
            self.assertEqual((self.result(db,7)['points_delta'],self.result(db,7,0)['points_delta']),(50,-50))
            standings=db.execute('SELECT player_id,points,wins,losses FROM arena_standings ORDER BY player_id').fetchall()
            self.assertEqual([tuple(r)[1:] for r in standings],[(20,1,7),(160,7,1)])
            self.assertEqual(self.result(db,8)['points_delta'],30)
            self.assertEqual(self.snapshot(db,'social_duels'),duels)
            self.assertEqual(self.snapshot(db,'players'),players)
            before=self.snapshot(db,'arena_results')
            self.assertEqual(balance.reconcile(db),0)
            self.assertEqual(self.snapshot(db,'arena_results'),before)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_balance_adjustments').fetchone()[0],2)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            db.commit()

    def test_month_and_profile_binding_prevent_using_present_day_identity(self):
        with site.app.app_context():
            db=site.get_db()
            self.event(db,1,when='2026-08-10T12:00:00+00:00')
            self.event(db,2,identity=False)
            balance.store_activity(db,'1001',proof(period='2026-09'))
            self.assertEqual(balance.reconcile(db),0)
            balance.store_activity(db,'9999',proof(profile='9999',period='2026-08'))
            db.execute('UPDATE players SET aomstats_profile_id=?,elo_1v1=1500 WHERE id=?',('9999',self.players[0]))
            self.assertEqual(balance.reconcile(db),0)
            balance.store_activity(db,'1001',proof(period='2026-08'))
            self.assertEqual(balance.reconcile(db),1)
            self.assertEqual(self.result(db,1)['rating_self'],900)
            self.assertEqual(self.result(db,2)['points_delta'],150)

    def test_zero_floor_restores_no_debt_and_current_elo_stays_untouched(self):
        with site.app.app_context():
            db=site.get_db()
            balance.store_activity(db,'1001',proof())
            self.event(db,1)
            loser=self.result(db,1,0)
            self.assertEqual((loser['points_delta'],loser['points_after']),(-50,0))
            self.event(db,2,False)
            self.assertEqual(self.result(db,2)['points_after'],30)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM players WHERE elo_1v1 IS NOT NULL').fetchone()[0],0)

    def test_upgrade_keeps_original_snapshots_and_revises_closed_awards(self):
        with site.app.app_context():
            db=site.get_db()
            self.event(db,1,when='2026-08-10T12:00:00+00:00')
            seasons.close_seasons(db,'2026-09')
            old_closed=db.execute("SELECT closed_at FROM arena_seasons WHERE season='2026-08'").fetchone()[0]
            for table in ('arena_results','arena_standings','arena_awards'):
                db.execute(f'DROP TABLE {table}_before_v28')
            db.execute("DELETE FROM site_meta WHERE key='arena_v28_prepared'")
            original=self.snapshot(db,'arena_results')
            balance.store_activity(db,'1001',proof(period='2026-08'))
            db.commit();seasons.init_arena(db);db.commit()
            self.assertEqual(self.snapshot(db,'arena_results_before_v28'),original)
            self.assertEqual(self.result(db,1)['points_delta'],50)
            self.assertEqual(db.execute('SELECT points FROM arena_awards WHERE player_id=?',(self.players[0],)).fetchone()[0],50)
            self.assertEqual(db.execute("SELECT closed_at FROM arena_seasons WHERE season='2026-08'").fetchone()[0],old_closed)
            after=self.snapshot(db,'arena_results')
            seasons.init_arena(db);db.commit()
            self.assertEqual(self.snapshot(db,'arena_results'),after)

    def test_failed_rebuild_rolls_back_every_point_and_audit(self):
        with site.app.app_context():
            db=site.get_db();self.event(db,1)
            balance.store_activity(db,'1001',proof());db.commit()
            before=self.snapshot(db,'arena_results')
            db.execute('BEGIN IMMEDIATE')
            with patch.object(balance,'rebuild_ladder',side_effect=RuntimeError('interrupted')):
                with self.assertRaises(RuntimeError):balance.reconcile(db)
            db.rollback()
            self.assertEqual(self.snapshot(db,'arena_results'),before)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_balance_adjustments').fetchone()[0],0)
            self.assertEqual(balance.reconcile(db),1)

    def test_incomplete_result_cannot_receive_half_a_repair(self):
        with site.app.app_context():
            db=site.get_db();self.event(db,1)
            db.execute('DELETE FROM arena_results WHERE won=0')
            balance.store_activity(db,'1001',proof())
            self.assertEqual(balance.reconcile(db),0)
            self.assertEqual(self.result(db,1)['points_delta'],150)

    def test_background_job_retries_failed_evidence_without_duplicate_requests(self):
        with site.app.app_context():
            db=site.get_db();self.event(db,1);db.commit()
            def fetched(profile):
                self.assertFalse(db.in_transaction)
                return proof(profile)
            with patch.object(balance,'fetch_activity',side_effect=fetched) as fetch:
                self.assertTrue(balance.process_one(db))
                self.assertFalse(balance.process_one(db))
                self.assertEqual(fetch.call_count,1)
            self.assertEqual(self.result(db,1)['points_delta'],50)

    def test_result_submission_fetches_ranked_activity_before_scoring(self):
        with site.app.app_context():
            db=site.get_db();db.executemany('UPDATE players SET elo_1v1=? WHERE id=?',zip([900,1200],self.players[:2]));db.commit()
        duel=self.create_challenge();self.login(1);self.post(f"/duelo/{duel['id']}/aceitar")
        result=dict(state='completed',match_url='https://aomstats.io/match/99115933',
                    winner_profile_id='1001',loser_profile_id='1002')
        with patch.object(site,'fetch_aomstats_match',return_value=result),patch.object(balance,'fetch_activity',return_value=proof()):
            response=self.post(f"/duelo/{duel['id']}/partida",match_id='99115933')
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.row('SELECT points_delta FROM arena_results WHERE won=1')['points_delta'],50)
        page=self.client.get(f"/duelo/{duel['id']}").get_data(as_text=True)
        self.assertIn('Benefício de atividade mensal aplicado',page)
        self.assertIn('+50 pts',page)

    def test_admin_review_is_private_and_post_requires_csrf(self):
        self.assertEqual(self.client.get('/admin/arena-pontos').status_code,302)
        self.login()
        self.assertEqual(self.client.get('/admin/arena-pontos').status_code,302)
        with self.client.session_transaction() as session:session['admin_id']=1
        self.assertEqual(self.client.get('/admin/arena-pontos').status_code,200)
        self.assertEqual(self.client.post('/admin/arena-pontos').status_code,400)
        self.assertEqual(self.post('/admin/arena-pontos').status_code,302)

    def test_team_requires_eight_for_every_winning_member(self):
        with site.app.app_context():
            db=site.get_db()
            fourth=db.execute("INSERT INTO players(nickname,aomstats_profile_id) VALUES('Quarto','1004')").lastrowid
            a,b=self.players[:2],self.players[2:]+[fourth]
            ta=db.execute("INSERT INTO arena_teams(name,size,captain_id) VALUES('A',2,?)",(a[0],)).lastrowid
            tb=db.execute("INSERT INTO arena_teams(name,size,captain_id) VALUES('B',2,?)",(b[0],)).lastrowid
            did=db.execute('''INSERT INTO arena_team_duels(team_a,team_b,size,name_a,name_b,captain_a,captain_b,
                share_token,status,winner_side,rating_a,rating_b,rating_source)
                VALUES(?,?,2,'A','B',?,?,'v28-team','completed','a',900,1200,'challenge')''',(ta,tb,a[0],b[0])).lastrowid
            for side,ids in [('a',a),('b',b)]:
                for pid in ids:
                    profile=db.execute('SELECT aomstats_profile_id FROM players WHERE id=?',(pid,)).fetchone()[0]
                    db.execute('INSERT INTO arena_duel_members VALUES(?,?,?,?)',(did,pid,side,profile))
            seasons.record_result(db,'2v2',did,a,b)
            balance.store_activity(db,'1001',proof('1001'))
            balance.store_activity(db,'1002',proof('1002',count=7))
            self.assertEqual(balance.reconcile(db),0)
            balance.store_activity(db,'1002',proof('1002'))
            self.assertEqual(balance.reconcile(db),1)
            self.assertEqual([r[0] for r in db.execute('SELECT points_delta FROM arena_results ORDER BY player_id')],[50,50,-50,-50])
