"""A real zero floor and an idempotent correction of V25 score debt."""
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import test_v22_flows as fixtures
import arena_seasons as seasons

site=fixtures.site


class ZeroFloorTests(unittest.TestCase):
    setUp=fixtures.SiteFlows.setUp

    def play(self,db,event,won=True,queue='x1',when=None):
        a,b=self.players[:2]
        seasons.record_result(db,queue,event,[a if won else b],[b if won else a],when)

    def test_one_win_seven_losses_then_win_gives_30_in_every_mode(self):
        with site.app.app_context():
            db=site.get_db()
            for queue in seasons.QUEUES:
                self.play(db,1,queue=queue)
                for i in range(2,9):self.play(db,i,False,queue)
                before=db.execute('SELECT * FROM arena_standings WHERE queue=? AND player_id=?',(queue,self.players[0])).fetchone()
                self.assertEqual((before['wins'],before['losses'],before['points'],before['score_balance']),(1,7,0,0))
                self.play(db,9,queue=queue);self.play(db,9,queue=queue)
                after=db.execute('SELECT * FROM arena_standings WHERE queue=? AND player_id=?',(queue,self.players[0])).fetchone()
                self.assertEqual((after['wins'],after['losses'],after['points'],after['score_balance']),(2,7,30,30))
            self.assertEqual(db.execute('SELECT COUNT(*) FROM arena_results WHERE balance_before<0 OR balance_after<0').fetchone()[0],0)

    def test_partial_loss_stops_at_zero_and_bonus_is_received_in_full(self):
        with site.app.app_context():
            db=site.get_db();self.play(db,1)
            # A residual score from the former -20 rule must also stop at zero.
            db.execute('UPDATE arena_standings SET points=10,score_balance=10 WHERE player_id=?',(self.players[0],))
            self.play(db,3,False)
            last=db.execute('SELECT * FROM arena_results WHERE event_id=3 AND player_id=?',(self.players[0],)).fetchone()
            self.assertEqual((last['points_before'],last['points_after'],last['points_delta']),(10,0,-30))
            with patch.object(seasons.arena_rules,'event_ratings',return_value=(1000,1200)):
                self.play(db,4)
            rank=db.execute('SELECT points,score_balance FROM arena_standings WHERE player_id=?',(self.players[0],)).fetchone()
            self.assertEqual(tuple(rank),(120,120))

    def test_migration_restores_wins_and_keeps_evidence_badges_and_archives(self):
        with site.app.app_context():
            db=site.get_db();pid=self.players[0];current=seasons.period()
            self.play(db,100,when='2026-08-10 12:00:00');seasons.close_seasons(db,current)
            stamp=seasons.utc_now().isoformat()
            with patch.object(seasons.arena_rules,'outcome_points',return_value=(30,-20)):
                for i,won in enumerate([True]+[False]*7+[True],1):self.play(db,i,won,when=stamp)
            # Reconstruct the debt that V25 stored for this player's exact history.
            balance=0
            for r in db.execute('SELECT * FROM arena_results WHERE season=? AND player_id=? ORDER BY rowid',(current,pid)).fetchall():
                before=balance;balance+=r['points_delta']
                db.execute('''UPDATE arena_results SET points_before=?,points_after=?,balance_before=?,balance_after=?,rules_version=25
                    WHERE queue=? AND event_id=? AND player_id=?''',
                    (max(0,before),max(0,balance),before,balance,r['queue'],r['event_id'],pid))
            self.assertEqual(balance,-80)
            db.execute('UPDATE arena_standings SET points=0,score_balance=-80 WHERE season=? AND player_id=?',(current,pid))
            old_evidence=[tuple(r) for r in db.execute('''SELECT queue,event_id,player_id,won,recorded_at,points_delta,
                rating_self,rating_opponent,demoted,emblem_before,emblem_after FROM arena_results ORDER BY rowid''')]
            old_archives=[tuple(r) for r in db.execute('SELECT * FROM arena_results WHERE season<>?',(current,))]
            old_awards=[tuple(r) for r in db.execute('SELECT * FROM arena_awards')]
            old_badges=[tuple(r) for r in db.execute('SELECT queue,player_id,wins,losses,emblem_points,loss_streak,loss_bank FROM arena_standings ORDER BY season,queue,player_id')]
            db.execute("DELETE FROM site_meta WHERE key='arena_v25_1_migrated'")
            for table in ['arena_results','arena_standings']:db.execute(f'DROP TABLE {table}_before_v25_1')
            db.commit();seasons.init_arena(db);db.commit()
            rank=db.execute('SELECT points,score_balance FROM arena_standings WHERE season=? AND player_id=?',(current,pid)).fetchone()
            self.assertEqual(tuple(rank),(30,30))
            self.assertEqual(db.execute('SELECT score_balance FROM arena_standings_before_v25_1 WHERE season=? AND player_id=?',(current,pid)).fetchone()[0],-80)
            self.assertEqual([tuple(r) for r in db.execute('''SELECT queue,event_id,player_id,won,recorded_at,points_delta,
                rating_self,rating_opponent,demoted,emblem_before,emblem_after FROM arena_results ORDER BY rowid''')],old_evidence)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_results WHERE season<>?',(current,))],old_archives)
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_awards')],old_awards)
            self.assertEqual([tuple(r) for r in db.execute('SELECT queue,player_id,wins,losses,emblem_points,loss_streak,loss_bank FROM arena_standings ORDER BY season,queue,player_id')],old_badges)
            before=[tuple(r) for r in db.execute('SELECT * FROM arena_results ORDER BY rowid')]
            seasons.init_arena(db);db.commit()
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_results ORDER BY rowid')],before)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_statement_shows_the_real_deduction_instead_of_debt(self):
        with site.app.test_request_context():
            template=site.app.jinja_env.get_template('_arena_points_statement.html')
            html=template.render(duel={'scoring':[dict(nickname='Jogador',points_before=10,points_after=0,
                balance_after=0,points_delta=-90,rules_version=251,rating_self=1200,rating_opponent=1099)]})
            cells=[cell.get_text(' ',strip=True) for cell in BeautifulSoup(html,'html.parser').select('tbody td')]
            self.assertEqual(cells[0],'Jogador');self.assertTrue(cells[1].startswith('-10 pts'))
            self.assertIn('piso zero',cells[1]);self.assertEqual(cells[2],'0 pts')
