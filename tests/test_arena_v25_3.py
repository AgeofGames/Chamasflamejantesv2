"""Repair the reported 5 W / 1 L / 130 pts case in an existing database."""
from datetime import datetime, timedelta
import json
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import test_arena_v24 as teams
import test_v22_flows as fixtures
import arena_rules as rules
import arena_seasons as seasons

site = fixtures.site


class ExistingSeasonRepairTests(unittest.TestCase):
    setUp = teams.TeamFlows.setUp

    def old_result(self, db, event, won=True, queue='x1', when=None, ratings=(None,None), loss=-20):
        size = {'x1':1,'2v2':2,'3v3':3}[queue]
        a,b = self.players[:size],self.players[size:2*size]
        winners,losers = (a,b) if won else (b,a)
        when = when or seasons.utc_now().isoformat()
        if queue=='x1':
            db.execute('''INSERT INTO social_duels
              (id,challenger_id,challenged_id,status,winner_id,loser_id,match_id,match_payload,
               requested_at,finished_at,share_token) VALUES(?,?,?,'completed',?,?,?,?,?,?,?)''',
              (event,a[0],b[0],winners[0],losers[0],str(90000000+event),
               json.dumps({'state':'completed'}),when,when,f'repair-{event}'))
        win_delta,loss_delta = rules.outcome_points(*ratings)
        if loss_delta == -30: loss_delta = loss
        with patch.object(rules,'outcome_points',return_value=(win_delta,loss_delta)), \
             patch.object(rules,'event_ratings',return_value=ratings):
            seasons.record_result(db,queue,event,winners,losers,when)
        db.execute('UPDATE arena_results SET rules_version=252 WHERE queue=? AND event_id=?',(queue,event))

    def ready_upgrade(self, db):
        # The fixture starts with all migrations applied; emulate an actual V25.2 DB.
        db.execute("DELETE FROM site_meta WHERE key='arena_v25_3_migrated'")
        for table in ('arena_results','arena_standings'):
            db.execute(f'DROP TABLE IF EXISTS {table}_before_v25_3')
        db.commit()

    def rows(self, db, table):
        return [tuple(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY rowid')]

    def test_makise_130_becomes_120_in_existing_ranking_profile_and_statement(self):
        with site.app.app_context():
            db=site.get_db();pid=self.players[0]
            for i,won in enumerate([True]*5+[False],1):self.old_result(db,i,won)
            before=db.execute('SELECT points,wins,losses FROM arena_standings WHERE player_id=?',(pid,)).fetchone()
            self.assertEqual(tuple(before),(130,5,1))
            evidence=self.rows(db,'social_duels'); players=self.rows(db,'players')
            self.ready_upgrade(db);seasons.init_arena(db);db.commit()
            result=db.execute('SELECT points,wins,losses,emblem_points FROM arena_standings WHERE player_id=?',(pid,)).fetchone()
            self.assertEqual(tuple(result),(120,5,1,120))
            backup=db.execute('SELECT points FROM arena_standings_before_v25_3 WHERE player_id=?',(pid,)).fetchone()
            self.assertEqual(backup['points'],130)
            self.assertEqual(self.rows(db,'social_duels'),evidence)
            self.assertEqual(self.rows(db,'players'),players)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        page=BeautifulSoup(self.client.get('/x1').data,'html.parser')
        row=next(r for r in page.select('.monthly-ranking-row') if 'Makise_Kurisu_00' in r.get_text())
        self.assertEqual(row.select_one('.rank-points').get_text(' ',strip=True),'120 PTS')
        self.assertIn('5 V · 1 D',row.get_text(' ',strip=True))
        for url in [f'/perfil/{pid}',f'/perfil/{pid}/card']:
            page=BeautifulSoup(self.client.get(url).data,'html.parser')
            self.assertEqual(page.select_one('.profile-emblem-points').get_text(' ',strip=True),'120 pontos')
        page=BeautifulSoup(self.client.get('/duelo/6').data,'html.parser')
        rows=page.select('.arena-points-statement tbody tr')
        entry=next(r for r in rows if 'Makise_Kurisu_00' in r.get_text())
        self.assertEqual([cell.get_text(' ',strip=True) for cell in entry.select('td')],['Makise_Kurisu_00','-30 pts','120 pts'])

    def test_zero_floor_keeps_match_order_and_full_next_win_in_all_modes(self):
        for order,expected in [([True]*5+[False],120),([False]+[True]*5,150),
                               ([True]+[False]*7+[True],30)]:
            with self.subTest(order=order):
                with site.app.app_context():
                    db=site.get_db()
                    db.execute('DELETE FROM arena_results');db.execute('DELETE FROM arena_standings');db.execute('DELETE FROM social_duels')
                    for queue in seasons.QUEUES:
                        for i,won in enumerate(order,1):self.old_result(db,i,won,queue)
                    self.ready_upgrade(db);seasons.init_arena(db);db.commit()
                    for queue in seasons.QUEUES:
                        size={'x1':1,'2v2':2,'3v3':3}[queue]
                        for pid in self.players[:size]:
                            rank=db.execute('SELECT points,score_balance,wins,losses FROM arena_standings WHERE queue=? AND player_id=?',(queue,pid)).fetchone()
                            self.assertEqual(tuple(rank),(expected,expected,sum(order),len(order)-sum(order)))
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_results WHERE balance_before<0 OR balance_after<0').fetchone()[0],0)

    def test_recorded_upset_bonuses_and_ratings_survive_current_profile_changes(self):
        with site.app.app_context():
            db=site.get_db();pid=self.players[0]
            for i in range(1,6):self.old_result(db,i)
            self.old_result(db,6,False)
            self.old_result(db,7,False,ratings=(1099,1200))
            self.old_result(db,8,True,ratings=(1000,1200))
            self.old_result(db,9,False)
            self.assertEqual(db.execute('SELECT points FROM arena_standings WHERE player_id=?',(pid,)).fetchone()[0],140)
            original=[tuple(r) for r in db.execute('SELECT event_id,player_id,won,recorded_at,rating_self,rating_opponent FROM arena_results ORDER BY rowid')]
            db.execute('UPDATE players SET elo_1v1=2500,elo_team=2500')
            self.ready_upgrade(db)
            with patch.object(rules,'event_ratings',side_effect=AssertionError('Old bonuses must not use a fresh lookup')):
                seasons.init_arena(db);db.commit()
            self.assertEqual(db.execute('SELECT points FROM arena_standings WHERE player_id=?',(pid,)).fetchone()[0],120)
            self.assertEqual([tuple(r) for r in db.execute('SELECT event_id,player_id,won,recorded_at,rating_self,rating_opponent FROM arena_results ORDER BY rowid')],original)
            self.assertEqual([r['points_delta'] for r in db.execute('SELECT points_delta FROM arena_results WHERE event_id IN (7,8) AND player_id=? ORDER BY event_id',(pid,))],[-90,120])

    def test_closed_month_awards_and_new_results_survive_restarts_without_replay(self):
        with site.app.app_context():
            db=site.get_db();a,b=self.players[:2]
            start=datetime.strptime(seasons.period(),'%Y-%m').replace(tzinfo=seasons.ZONE)
            for i,won in enumerate([True]*5+[False],1):
                self.old_result(db,i,won,when=(start-timedelta(days=2)+timedelta(minutes=i)).isoformat())
            seasons.close_seasons(db)
            for i,won in enumerate([True]*5+[False],10):self.old_result(db,i,won)
            awards=self.rows(db,'arena_awards')
            past=[tuple(r) for r in db.execute('SELECT * FROM arena_results WHERE season<>?',(seasons.period(),))]
            past_ranks=[tuple(r) for r in db.execute('SELECT * FROM arena_standings WHERE season<>?',(seasons.period(),))]
            self.ready_upgrade(db);seasons.init_arena(db);db.commit()
            self.assertEqual(self.rows(db,'arena_awards'),awards)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_results WHERE season<>?',(seasons.period(),))],past)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_standings WHERE season<>?',(seasons.period(),))],past_ranks)
            seasons.record_result(db,'x1',90,[a],[b]);db.commit()
            results=self.rows(db,'arena_results');standings=self.rows(db,'arena_standings')
            backups=self.rows(db,'arena_standings_before_v25_3')
            seasons.init_arena(db);db.commit();seasons.record_result(db,'x1',90,[a],[b]);db.commit()
            self.assertEqual(self.rows(db,'arena_results'),results)
            self.assertEqual(self.rows(db,'arena_standings'),standings)
            self.assertEqual(self.rows(db,'arena_standings_before_v25_3'),backups)
            self.assertEqual(db.execute('SELECT points FROM arena_standings WHERE season=? AND player_id=?',(seasons.period(),a)).fetchone()[0],150)

    def test_badge_replay_preserves_demotion_rules_separate_from_ranking_points(self):
        with site.app.app_context():
            db=site.get_db();pid=self.players[0]
            for i,won in enumerate([True]*8+[False,True,False,True,False,True,False],1):self.old_result(db,i,won)
            self.ready_upgrade(db);seasons.init_arena(db);db.commit()
            rank=db.execute('SELECT points,emblem_points,loss_streak,loss_bank,wins,losses FROM arena_standings WHERE player_id=?',(pid,)).fetchone()
            self.assertEqual(tuple(rank),(210,199,0,0,11,4))

    def test_nullable_legacy_deltas_use_only_stored_elo_and_default_to_base(self):
        with site.app.app_context():
            db=site.get_db();pid=self.players[0]
            self.old_result(db,1,ratings=(1000,1200));self.old_result(db,2,False)
            db.execute('UPDATE arena_results SET points_delta=NULL')
            self.ready_upgrade(db);seasons.init_arena(db);db.commit()
            deltas=[r[0] for r in db.execute('SELECT points_delta FROM arena_results WHERE player_id=? ORDER BY event_id',(pid,))]
            self.assertEqual(deltas,[120,-30])
            self.assertEqual(db.execute('SELECT points FROM arena_standings WHERE player_id=?',(pid,)).fetchone()[0],90)

    def test_failed_repair_rolls_back_scores_backup_and_marker_together(self):
        with site.app.app_context():
            db=site.get_db()
            for i,won in enumerate([True]*5+[False],1):self.old_result(db,i,won)
            self.ready_upgrade(db)
            results=self.rows(db,'arena_results');standings=self.rows(db,'arena_standings')
            calculate=seasons.result_progress;calls=0
            def fail_during_replay(*args):
                nonlocal calls
                calls+=1
                if calls==4:raise RuntimeError('simulated failure')
                return calculate(*args)
            with patch.object(seasons,'result_progress',side_effect=fail_during_replay):
                with self.assertRaises(RuntimeError):seasons.init_arena(db)
            db.rollback()
            self.assertEqual(self.rows(db,'arena_results'),results)
            self.assertEqual(self.rows(db,'arena_standings'),standings)
            self.assertIsNone(db.execute("SELECT 1 FROM site_meta WHERE key='arena_v25_3_migrated'").fetchone())
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='arena_results_before_v25_3'").fetchone())
            seasons.init_arena(db);db.commit()
            self.assertEqual(db.execute('SELECT points FROM arena_standings WHERE player_id=?',(self.players[0],)).fetchone()[0],120)
