"""Standard losses, monthly community tag and the lifetime of a formed duo."""
import secrets
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
import test_v22_flows as fixtures
import test_arena_v24 as teams
import arena_rules as rules
import arena_seasons as seasons

site = fixtures.site


class CommunityTagTests(unittest.TestCase):
    setUp = fixtures.SiteFlows.setUp
    login = fixtures.SiteFlows.login
    post = fixtures.SiteFlows.post
    row = fixtures.SiteFlows.row
    create_challenge = fixtures.SiteFlows.create_challenge

    def challenge(self, sender, target, status='pending', stamp=None):
        with site.app.app_context():
            db = site.get_db()
            did = db.execute('''INSERT INTO social_duels(challenger_id,challenged_id,status,requested_at,share_token)
              VALUES(?,?,?,?,?)''', (self.players[sender],self.players[target],status,
                                  stamp or seasons.utc_now().isoformat(), secrets.token_urlsafe(18))).lastrowid
            db.commit()
            return did

    def test_tag_tracks_received_challenges_ties_and_cancellations(self):
        with site.app.app_context():
            self.assertEqual(rules.most_challenged(site.get_db()), {})
        first = self.create_challenge()
        self.login(1); self.post(f"/duelo/{first['id']}/recusar")
        self.challenge(2,1,'completed')
        self.challenge(1,0)
        for who, count in [(1,2),(0,0),(2,0)]:
            with site.app.test_request_context():
                self.assertEqual(site.social_most_challenged(self.players[who]),count)
        self.login(2); self.post(f'/perfil/{self.players[0]}/desafiar')
        current = self.row("SELECT * FROM social_duels WHERE challenger_id=? AND challenged_id=?",
                           (self.players[2],self.players[0]))
        with site.app.app_context():
            self.assertEqual(rules.most_challenged(site.get_db()), {self.players[0]:2,self.players[1]:2})
        self.post(f"/duelo/{current['id']}/cancelar")
        with site.app.app_context():
            self.assertEqual(rules.most_challenged(site.get_db()), {self.players[1]:2})

    def test_brasilia_month_boundaries_december_and_deleted_accounts(self):
        for stamp in ['2026-09-01 02:59:59','2026-10-01 03:00:00']:
            self.challenge(0,1,stamp=stamp)
        self.challenge(0,2,stamp='2026-09-01T03:00:00Z')
        self.challenge(1,2,stamp='2026-10-01T02:59:59+00:00')
        with site.app.app_context():
            db=site.get_db()
            self.assertEqual(rules.most_challenged(db,'2026-09-10'),{self.players[2]:2})
            db.execute('UPDATE players SET is_active=0 WHERE id=?',(self.players[2],))
            self.assertEqual(rules.most_challenged(db,'2026-09-10'),{})
            db.commit()
        self.challenge(1,0,stamp='2027-01-01T02:59:59Z')
        with site.app.app_context():
            self.assertEqual(rules.most_challenged(site.get_db(),'2026-12-31'),{self.players[0]:1})
            self.assertEqual(rules.most_challenged(site.get_db(),'2027-01-02'),{})

    def test_tag_shows_in_public_profile_popup_roster_and_ranking_with_one_query(self):
        self.challenge(0,1)
        with site.app.test_request_context():
            with patch.object(rules,'most_challenged',wraps=rules.most_challenged) as query:
                site.social_roster(); site.duel_ranking(); site.social_most_challenged(self.players[1])
                self.assertEqual(query.call_count,1)
        for path in [f'/perfil/{self.players[1]}',f'/perfil/{self.players[1]}/card','/x1']:
            page=BeautifulSoup(self.client.get(path).data,'html.parser')
            self.assertIsNotNone(page.select_one('.most-challenged-tag'),path)
        page=BeautifulSoup(self.client.get('/x1').data,'html.parser')
        self.assertEqual(len(page.select('.social-player-card .most-challenged-tag')),1)
        self.assertEqual(len(page.select('.monthly-ranking-row .most-challenged-tag')),1)
        self.assertIsNotNone(page.select_one('.monthly-ranking-row .rank-emblem'))

    def test_notification_migration_preserves_scores_and_new_defeats_cost_30(self):
        with site.app.app_context():
            db=site.get_db(); a,b=self.players[:2]
            with patch.object(rules,'outcome_points',return_value=(30,-20)):
                seasons.record_result(db,'x1',1,[a],[b])
                seasons.record_result(db,'x1',2,[b],[a])
            saved=[tuple(r) for r in db.execute('SELECT * FROM arena_results ORDER BY rowid')]
            db.execute("DELETE FROM site_meta WHERE key='arena_v25_2_migrated'")
            db.commit(); seasons.init_arena(db); db.commit()
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM arena_results ORDER BY rowid')],saved)
            seasons.record_result(db,'x1',3,[a],[b])
            loss=db.execute('SELECT * FROM arena_results WHERE event_id=3 AND won=0').fetchone()
            self.assertEqual((loss['points_delta'],loss['points_before'],loss['points_after'],loss['rules_version']),(-30,30,0,253))


class DuoLifecycleTests(unittest.TestCase):
    setUp=teams.TeamFlows.setUp
    login=fixtures.SiteFlows.login
    post=fixtures.SiteFlows.post
    row=fixtures.SiteFlows.row
    make_team=teams.TeamFlows.make_team
    make_duel=teams.TeamFlows.make_duel

    def profile(self, who, popup=False):
        return BeautifulSoup(self.client.get(f'/perfil/{self.players[who]}'+('/card' if popup else '')).data,'html.parser')

    def test_acceptance_removes_invitation_but_notice_waits_for_inviter_to_read(self):
        tid=self.make_team(0,[1],'Parceria',accept=False)
        for who in [0,1]: self.assertIsNone(self.profile(who).select_one('[data-profile-duo]'))
        self.login(1)
        before=self.client.get('/api/notificacoes').get_json()
        self.assertIn('ACEITAR CONVITE',before['html'])
        self.post(f'/arena/equipe/{tid}/responder',answer='accept')
        after=self.client.get('/api/notificacoes?cursor='+before['cursor']).get_json()
        self.assertNotIn('ACEITAR CONVITE',after['html']); self.assertEqual(after['unread'],0)
        for who in [0,1]:
            for popup in [False,True]:
                card=self.profile(who,popup).select_one('[data-profile-duo]')
                self.assertEqual(card['data-profile-duo'],str(tid))
                self.assertIn('Parceria',card.get_text())
                self.assertEqual(len(card.select('.profile-duo-members>a')),2)
        # Visiting as the recipient or a third party cannot read the inviter's notice.
        self.client.get(f'/arena/equipe/{tid}')
        self.login(2); self.client.get(f'/arena/equipe/{tid}')
        self.login(0); self.profile(0)
        notice=self.client.get('/api/notificacoes').get_json()
        self.assertEqual(notice['unread'],1); self.assertIn('aceitou o convite',notice['html'])
        self.assertEqual(self.client.get('/api/notificacoes?cursor='+notice['cursor']).status_code,204)
        self.client.get(f'/arena/equipe/{tid}')
        read=self.client.get('/api/notificacoes?cursor='+notice['cursor']).get_json()
        self.assertNotIn('aceitou o convite',read['html']); self.assertEqual(read['unread'],0)
        self.assertIsNotNone(self.profile(0).select_one('[data-profile-duo]'))
        self.assertIsNotNone(self.profile(1).select_one('[data-profile-duo]'))

    def test_either_accepted_member_can_disband_from_profile_and_form_another_duo(self):
        for actor in [0,1]:
            tid=self.make_team(0,[1],f'Dupla {actor}')
            self.login(actor)
            for popup in [False,True]:
                form=self.profile(actor,popup).select_one(f'form[action="/arena/equipe/{tid}/sair"]')
                self.assertIsNotNone(form); self.assertEqual(form.select_one('[name="return_to"]')['value'],'profile')
            response=self.post(f'/arena/equipe/{tid}/sair',return_to='profile')
            self.assertEqual(response.location,f'/perfil/{self.players[actor]}')
            self.assertEqual(self.row('SELECT archived FROM arena_teams WHERE id=?',(tid,))['archived'],1)
            for who in [0,1]:self.assertIsNone(self.profile(who).select_one('[data-profile-duo]'))
            self.assertEqual(self.client.get(f'/arena/equipe/{tid}').status_code,200)
        self.assertIsNotNone(self.make_team(0,[1],'Nova dupla'))

    def test_controls_in_2x2_and_no_permission_for_visitors_or_invited_players(self):
        tid=self.make_team(0,[1],'Protegida',accept=False)
        self.login(1)
        self.assertEqual(self.post(f'/arena/equipe/{tid}/sair').status_code,403)
        self.post(f'/arena/equipe/{tid}/responder',answer='accept')
        self.login(2)
        self.assertIsNone(self.profile(0).select_one('.arena-team-leave'))
        self.assertEqual(self.post(f'/arena/equipe/{tid}/sair').status_code,403)
        self.login(1)
        self.assertEqual(self.client.post(f'/arena/equipe/{tid}/sair',data={}).status_code,400)
        page=BeautifulSoup(self.client.get('/arena/equipes?modo=2v2').data,'html.parser')
        form=page.select_one(f'form[action="/arena/equipe/{tid}/sair"]')
        self.assertEqual(form.select_one('[name="return_to"]')['value'],'arena')
        response=self.post(f'/arena/equipe/{tid}/sair',return_to='arena')
        self.assertEqual(response.location,'/arena/equipes?modo=2v2')
        self.assertNotIn('Protegida',self.client.get('/arena/equipes?modo=2v2').get_data(as_text=True))

    def test_busy_duo_cannot_be_disbanded_and_completed_history_survives(self):
        duel=self.make_duel(); tid=duel['team_a']
        self.login(1)
        self.assertIsNotNone(self.profile(1).select_one('.arena-team-leave button[disabled]'))
        self.post(f'/arena/equipe/{tid}/sair',return_to='profile')
        self.assertEqual(self.row('SELECT archived FROM arena_teams WHERE id=?',(tid,))['archived'],0)
        with site.app.app_context():
            db=site.get_db()
            db.execute("UPDATE arena_team_duels SET status='completed',winner_side='a',match_id='12345' WHERE id=?",(duel['id'],))
            seasons.record_result(db,'2v2',duel['id'],self.players[:2],self.players[2:4])
            scores=[tuple(r) for r in db.execute('SELECT * FROM arena_results ORDER BY rowid')]
            db.commit()
        self.post(f'/arena/equipe/{tid}/sair')
        self.assertEqual(self.row('SELECT COUNT(*) n FROM arena_duel_members')['n'],4)
        self.assertEqual(self.client.get(f"/arena/equipes/duelo/{duel['id']}").status_code,200)
        self.assertIn('12345',self.client.get(f'/arena/equipe/{tid}').get_data(as_text=True))
        with site.app.app_context():
            self.assertEqual([tuple(r) for r in site.get_db().execute('SELECT * FROM arena_results ORDER BY rowid')],scores)

    def test_trio_partner_leaving_does_not_archive_the_remaining_team(self):
        tid=self.make_team(0,[1,2],'Trio')
        self.login(1);self.post(f'/arena/equipe/{tid}/sair')
        self.assertEqual(self.row('SELECT archived FROM arena_teams WHERE id=?',(tid,))['archived'],0)
        self.assertEqual(self.row('SELECT state FROM arena_team_members WHERE team_id=? AND player_id=?',
                                  (tid,self.players[1]))['state'],'left')

    def test_legacy_acceptance_notices_migrate_once_and_do_not_disappear_on_disband(self):
        tid=self.make_team(0,[1],'Antiga')
        with site.app.app_context():
            db=site.get_db()
            db.execute("UPDATE social_notifications SET kind='team' WHERE kind='team_accepted'")
            db.execute("DELETE FROM site_meta WHERE key='arena_v25_2_migrated'")
            db.commit();seasons.init_arena(db);db.commit();seasons.init_arena(db);db.commit()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM social_notifications WHERE kind='team_accepted'").fetchone()[0],1)
        self.login(1); self.post(f'/arena/equipe/{tid}/sair')
        self.login(0)
        feed=self.client.get('/api/notificacoes').get_json()
        self.assertIn('aceitou o convite',feed['html']);self.assertIn('foi desfeita',feed['html'])
        self.client.get(f'/arena/equipe/{tid}')
        self.assertEqual(self.client.get('/api/notificacoes').get_json()['unread'],0)

    def test_repeated_accept_and_decline_do_not_leave_stale_invitation_actions(self):
        tid=self.make_team(0,[1],'Convites',accept=False)
        self.login(1);self.post(f'/arena/equipe/{tid}/responder',answer='decline')
        self.assertNotIn('ACEITAR CONVITE',self.client.get('/api/notificacoes').get_json()['html'])
        self.login(0);self.post(f'/arena/equipe/{tid}/convidar',player_id=self.players[1])
        self.login(1)
        self.assertEqual(self.client.get('/api/notificacoes').get_json()['html'].count('ACEITAR CONVITE'),1)
        self.post(f'/arena/equipe/{tid}/responder',answer='accept')
        self.assertEqual(self.post(f'/arena/equipe/{tid}/responder',answer='accept').status_code,403)
        self.assertEqual(self.row("SELECT COUNT(*) n FROM social_notifications WHERE kind='team_accepted'")['n'],1)
