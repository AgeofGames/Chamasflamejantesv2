"""Team Arena. Reuses Google accounts, notifications, avatars and match sources."""
from functools import lru_cache
import hashlib
import json
import secrets
import sqlite3
import time

from flask import abort, flash, redirect, render_template, request, url_for, jsonify
from aomstats_matches import lookup_match
import arena_seasons
import arena_rules
from share_cards import render_team_card

ACTIVE = ('pending','accepted','match_pending')

def remove_player(db, pid):
    db.execute("""UPDATE arena_team_duels SET status='cancelled',finished_at=CURRENT_TIMESTAMP
      WHERE status IN ('pending','accepted','match_pending') AND id IN
      (SELECT duel_id FROM arena_duel_members WHERE player_id=?)""",(pid,))
    db.execute("""UPDATE arena_teams SET archived=1 WHERE id IN
      (SELECT team_id FROM arena_team_members WHERE player_id=? AND state='accepted')""",(pid,))
    db.execute("UPDATE arena_team_members SET state='left' WHERE player_id=?",(pid,))

def install_teams(app, api):
    def db(): return api['get_db']()
    def account(): return api['current_social_account']()
    def player(pid): return api['social_player_payload'](api['get_social_player'](pid))
    def viewer_id(): return account()['player_id']
    def csrf(): api['require_csrf']()
    protected = api['social_profile_required']

    def notify(pid, actor, path, message, kind='team'):
        owner = api['social_account_for_player'](pid)
        if owner:
            db().execute('''INSERT INTO social_notifications(account_id,actor_player_id,kind,message,arena_url)
              VALUES(?,?,?,?,?)''',(owner['id'],actor,kind,message[:500],path))

    def eligible(pid):
        return db().execute('''SELECT p.id FROM players p JOIN social_accounts sa ON sa.player_id=p.id
          WHERE p.id=? AND p.is_active=1 AND p.aomstats_profile_id<>'' AND p.aomstats_url<>'' ''',(pid,)).fetchone()

    def membership(pid,size):
        return db().execute('''SELECT t.id FROM arena_teams t JOIN arena_team_members m ON m.team_id=t.id
          WHERE t.archived=0 AND t.size=? AND m.player_id=? AND m.state='accepted' ''',(size,pid)).fetchone()

    def team(tid):
        row = db().execute('SELECT * FROM arena_teams WHERE id=?',(tid,)).fetchone()
        if not row: abort(404)
        data = dict(row)
        members = db().execute('''SELECT m.*,p.nickname,p.nickname_color,p.aomstats_profile_id,p.avatar_url,p.avatar_file,
          p.is_active,sa.id account_id FROM arena_team_members m JOIN players p ON p.id=m.player_id
          LEFT JOIN social_accounts sa ON sa.player_id=p.id WHERE team_id=? ORDER BY m.player_id=? DESC,m.player_id''',
          (tid,row['captain_id'])).fetchall()
        data['members'] = [dict(m,id=m['player_id']) for m in members if m['state'] in ('invited','accepted')]
        accepted = [m for m in data['members'] if m['state']=='accepted' and m['is_active'] and m['account_id'] and m['aomstats_profile_id']]
        data['ready'] = not row['archived'] and len(accepted)==row['size'] and len(data['members'])==row['size']
        data['accepted'] = len(accepted)
        data['busy'] = bool(db().execute("""SELECT 1 FROM arena_team_duels WHERE (team_a=? OR team_b=?)
          AND status IN ('pending','accepted','match_pending') LIMIT 1""",(tid,tid)).fetchone())
        return data

    def profile_duo(pid):
        row = membership(pid, 2)
        if row:
            data = team(row['id'])
            if data['ready']:
                return data
        return None

    app.jinja_env.globals['arena_profile_duo'] = profile_duo

    def duel(did):
        row = db().execute('SELECT * FROM arena_team_duels WHERE id=?',(did,)).fetchone()
        if not row or row['status']=='cancelled': abort(404)
        data = dict(row)
        roster = db().execute('SELECT * FROM arena_duel_members WHERE duel_id=? ORDER BY side,player_id',(did,)).fetchall()
        api['prime_social_players']([r['player_id'] for r in roster])
        data['members'] = [dict(r,profile=player(r['player_id'])) for r in roster]
        data['scoring'] = [dict(r) for r in db().execute('''SELECT r.*,p.nickname FROM arena_results r
          JOIN players p ON p.id=r.player_id WHERE r.queue=? AND r.event_id=? ORDER BY r.won DESC,r.player_id''',
          (f"{row['size']}v{row['size']}",did))]
        data['a'] = [m for m in data['members'] if m['side']=='a']
        data['b'] = [m for m in data['members'] if m['side']=='b']
        data['label'] = api['SOCIAL_DUEL_LABELS'].get(row['status'],'Duelo de equipes')
        try: data['result'] = json.loads(row['match_payload'] or '{}')
        except ValueError: data['result'] = {}
        data['title'] = (f"{row['name_a'] if row['winner_side']=='a' else row['name_b']} venceu "
                         f"{row['name_b'] if row['winner_side']=='a' else row['name_a']}") if row['status']=='completed' else f"{row['name_a']} × {row['name_b']}"
        data['title'] += f" • Arena {row['size']}×{row['size']}"
        signature = json.dumps([row['status'],row['match_id'],row['winner_side'],
            [(m['profile']['nickname'],m['profile'].get('avatar_file'),m['profile'].get('avatar_url')) for m in data['members']]])
        version = hashlib.sha256(signature.encode()).hexdigest()[:12]
        data['image'] = api['absolute_site_url'](url_for('teams_image',token=row['share_token'],v=version))
        data['url'] = api['absolute_site_url'](url_for('teams_duel',did=did,card=version))
        data['download'] = url_for('teams_image',token=row['share_token'],download=1,v=version)
        return data

    def team_ids(data): return {m['player_id'] for m in data['members'] if m['state']=='accepted'}
    def notify_duel(data,actor,message):
        for m in data['members']:
            if m['player_id']!=actor: notify(m['player_id'],actor,url_for('teams_duel',did=data['id']),message)

    @app.get('/arena/equipes')
    def teams_arena():
        size = 3 if request.args.get('modo')=='3v3' else 2
        queue = f'{size}v{size}'
        viewer = account()
        pid = viewer['player_id'] if viewer else None
        page = max(1,request.args.get('pagina',1,type=int) or 1)
        total = db().execute('SELECT COUNT(*) FROM arena_teams WHERE archived=0 AND size=?',(size,)).fetchone()[0]
        pages = max(1,(total+23)//24); page=min(page,pages)
        rows = db().execute('SELECT id FROM arena_teams WHERE archived=0 AND size=? ORDER BY id DESC LIMIT 24 OFFSET ?',
                            (size,(page-1)*24)).fetchall()
        mine = db().execute('''SELECT t.id FROM arena_teams t JOIN arena_team_members m ON m.team_id=t.id
          WHERE t.archived=0 AND m.player_id=? AND m.state IN ('accepted','invited') ORDER BY t.id DESC''',(pid,)).fetchall() if pid else []
        return render_template('arena_teams.html', teams=[team(r['id']) for r in rows], mine=[team(r['id']) for r in mine],
            roster=[p for p in api['social_roster']() if p['social_enabled'] and p['id']!=pid],
            size=size,queue=queue,season=arena_seasons.period(),ranking=api['duel_ranking'](queue),page=page,pages=pages)

    @app.post('/arena/equipes/criar')
    @protected
    def teams_create():
        csrf(); pid=viewer_id()
        name=' '.join(request.form.get('name','').split())
        size=request.form.get('size',type=int)
        invitees=request.form.getlist('members',type=int)
        if not 2<=len(name)<=40 or size not in (2,3) or len(invitees)!=size-1 or len(set(invitees))!=len(invitees) or pid in invitees:
            flash('Dê um nome de 2 a 40 caracteres e escolha um parceiro para duplas ou dois para trios.','error')
            return redirect(url_for('teams_arena'))
        db().execute('BEGIN IMMEDIATE')
        if membership(pid,size) or not all(eligible(i) for i in invitees):
            db().rollback(); flash('Você já integra uma equipe desta modalidade ou um convidado não tem perfil ativo.','error')
            return redirect(url_for('teams_arena',modo=f'{size}v{size}'))
        tid=db().execute('INSERT INTO arena_teams(name,size,captain_id) VALUES(?,?,?)',(name,size,pid)).lastrowid
        db().execute("INSERT INTO arena_team_members VALUES(?,?,'accepted',CURRENT_TIMESTAMP)",(tid,pid))
        for invited in invitees:
            db().execute("INSERT INTO arena_team_members VALUES(?,?,'invited','')",(tid,invited))
            notify(invited,pid,url_for('teams_profile',tid=tid),f"Convite para a equipe {name}. Aceite para formar a equipe.",'team_invite')
        db().commit()
        flash('Convites enviados nas notificações. A equipe fica pronta quando todos aceitarem.','success')
        return redirect(url_for('teams_profile',tid=tid))

    @app.get('/arena/equipe/<int:tid>')
    def teams_profile(tid):
        data=team(tid)
        viewer=account(); pid=viewer['player_id'] if viewer else None
        mine=[team(r['id']) for r in db().execute('SELECT id FROM arena_teams WHERE captain_id=? AND archived=0 AND size=?',(pid,data['size']))] if pid else []
        if viewer:
            db().execute('UPDATE social_notifications SET is_read=1 WHERE account_id=? AND arena_url=?',(viewer['account_id'],url_for('teams_profile',tid=tid)))
            db().commit()
        history=db().execute("SELECT * FROM arena_team_duels WHERE (team_a=? OR team_b=?) AND status<>'cancelled' ORDER BY id DESC LIMIT 12",(tid,tid)).fetchall()
        return render_template('arena_team_profile.html',team=data,mine=mine,team_history=history,
            roster=[p for p in api['social_roster']() if p['social_enabled'] and p['id'] not in {m['player_id'] for m in data['members']}])

    @app.post('/arena/equipe/<int:tid>/responder')
    @protected
    def teams_join(tid):
        csrf(); pid=viewer_id(); db().execute('BEGIN IMMEDIATE'); data=team(tid)
        member=db().execute('SELECT * FROM arena_team_members WHERE team_id=? AND player_id=?',(tid,pid)).fetchone()
        if data['archived'] or not member or member['state']!='invited': db().rollback(); abort(403)
        answer=request.form.get('answer')
        if answer not in ('accept','decline'): db().rollback(); abort(400)
        if answer=='accept' and membership(pid,data['size']):
            db().rollback(); flash('Você já faz parte de uma equipe desta modalidade. Saia dela antes de aceitar.','error')
            return redirect(url_for('teams_profile',tid=tid))
        db().execute('UPDATE arena_team_members SET state=?,responded_at=CURRENT_TIMESTAMP WHERE team_id=? AND player_id=?',
                     ('accepted' if answer=='accept' else 'declined',tid,pid))
        db().execute("DELETE FROM social_notifications WHERE account_id=? AND arena_url=? AND kind='team_invite'",
                     (account()['account_id'],url_for('teams_profile',tid=tid)))
        notify(data['captain_id'],pid,url_for('teams_profile',tid=tid),
               f"{account()['nickname']} {'aceitou' if answer=='accept' else 'recusou'} o convite para {data['name']}.",
               'team_accepted' if answer=='accept' else 'team')
        db().commit(); return redirect(url_for('teams_profile',tid=tid))

    @app.post('/arena/equipe/<int:tid>/convidar')
    @protected
    def teams_invite(tid):
        csrf(); pid=viewer_id(); db().execute('BEGIN IMMEDIATE'); data=team(tid)
        invited=request.form.get('player_id',type=int)
        if data['captain_id']!=pid or data['archived']: db().rollback(); abort(403)
        if data['busy'] or len(data['members'])>=data['size'] or invited in {m['player_id'] for m in data['members']} or not eligible(invited):
            db().rollback(); flash('A equipe não tem uma vaga disponível ou o perfil não está ativo.','error')
        else:
            db().execute("""INSERT INTO arena_team_members VALUES(?,?,'invited','')
              ON CONFLICT(team_id,player_id) DO UPDATE SET state='invited',responded_at='' """,(tid,invited))
            notify(invited,pid,url_for('teams_profile',tid=tid),f"Você foi convidado para {data['name']}.",'team_invite')
            db().commit()
        return redirect(url_for('teams_profile',tid=tid))

    @app.post('/arena/equipe/<int:tid>/sair')
    @protected
    def teams_leave(tid):
        csrf(); pid=viewer_id(); db().execute('BEGIN IMMEDIATE'); data=team(tid)
        if data['archived'] or pid not in {m['player_id'] for m in data['members'] if m['state']=='accepted'}: db().rollback(); abort(403)
        if data['busy']:
            db().rollback(); flash('Conclua o duelo ativo antes de alterar a equipe. Um desafio sem aceite pode ser cancelado pelo capitão.','error')
        else:
            if data['size']==2 or data['captain_id']==pid:
                db().execute('UPDATE arena_teams SET archived=1 WHERE id=?',(tid,))
                for m in data['members']:
                    if m['player_id']!=pid:
                        notify(m['player_id'],pid,url_for('teams_profile',tid=tid),
                               f"A {'dupla' if data['size']==2 else 'equipe'} {data['name']} foi desfeita. Seu histórico foi preservado.",
                               'team_closed')
            else:
                db().execute("UPDATE arena_team_members SET state='left' WHERE team_id=? AND player_id=?",(tid,pid))
                notify(data['captain_id'],pid,url_for('teams_profile',tid=tid),f"{account()['nickname']} saiu da equipe {data['name']}.")
            db().commit()
            flash('Dupla desfeita. Os perfis foram atualizados e o histórico foi preservado.' if data['size']==2
                  else 'Equipe atualizada. O histórico foi preservado.','success')
        if request.form.get('return_to')=='profile':
            return redirect(url_for('social_profile',player_id=pid))
        if request.form.get('return_to')=='arena':
            return redirect(url_for('teams_arena',modo=f"{data['size']}v{data['size']}"))
        return redirect(url_for('teams_profile',tid=tid))

    @app.post('/arena/equipe/<int:tid>/desafiar')
    @protected
    def teams_challenge(tid):
        csrf(); pid=viewer_id(); mine_id=request.form.get('team_id',type=int)
        if not mine_id or mine_id==tid: abort(400)
        db().execute('BEGIN IMMEDIATE'); a,b=team(mine_id),team(tid)
        if a['captain_id']!=pid: db().rollback(); abort(403)
        if not a['ready'] or not b['ready'] or a['size']!=b['size'] or team_ids(a)&team_ids(b) or a['busy'] or b['busy']:
            db().rollback(); flash('As duas equipes precisam estar completas, na mesma modalidade e sem outro duelo ativo.','error')
            return redirect(url_for('teams_profile',tid=tid))
        queue = f"{a['size']}v{a['size']}"
        rules = arena_rules.challenge_check(db(),team_ids(a),team_ids(b),queue)
        if not rules['allowed']:
            db().rollback(); flash(rules['reason'],'error')
            return redirect(url_for('teams_profile',tid=tid))
        did=db().execute('''INSERT INTO arena_team_duels(team_a,team_b,size,name_a,name_b,captain_a,captain_b,message,share_token,
          rating_a,rating_b,rating_source) VALUES(?,?,?,?,?,?,?,?,?,?,?,'challenge')''',
          (mine_id,tid,a['size'],a['name'],b['name'],pid,b['captain_id'],
          request.form.get('message','Preparem-se para a batalha!').strip()[:280],secrets.token_urlsafe(18),
          rules['rating_a'],rules['rating_b'])).lastrowid
        arena_rules.record_attempt(db(),queue,did,team_ids(a),team_ids(b))
        for side,data in [('a',a),('b',b)]:
            for m in data['members']:
                db().execute('INSERT INTO arena_duel_members VALUES(?,?,?,?)',(did,m['player_id'],side,m['aomstats_profile_id']))
                if m['player_id']!=pid: notify(m['player_id'],pid,url_for('teams_duel',did=did),f"{a['name']} desafiou {b['name']} para {a['size']}×{a['size']}.",'team_challenge')
        db().commit(); return redirect(url_for('teams_duel',did=did))

    @app.get('/arena/equipes/duelo/<int:did>')
    def teams_duel(did):
        data=duel(did); viewer=account(); pid=viewer['player_id'] if viewer else None
        if viewer:
            db().execute('UPDATE social_notifications SET is_read=1 WHERE account_id=? AND arena_url=?',(viewer['account_id'],url_for('teams_duel',did=did)))
            db().commit()
        return render_template('arena_team_duel.html',duel=data,participant=pid in {m['player_id'] for m in data['members']},
                               share=api['build_share_links'](data['url'],data['title']))

    @app.post('/arena/equipes/duelo/<int:did>/responder')
    @protected
    def teams_respond(did):
        csrf(); pid=viewer_id(); db().execute('BEGIN IMMEDIATE'); data=duel(did)
        action=request.form.get('answer')
        if action not in ('accept','decline','cancel'): db().rollback(); abort(400)
        if pid!=(data['captain_a'] if action=='cancel' else data['captain_b']): db().rollback(); abort(403)
        if data['status']!='pending':
            db().rollback(); flash('Este desafio já foi respondido.','error'); return redirect(url_for('teams_duel',did=did))
        if action=='cancel':
            db().execute('DELETE FROM social_notifications WHERE arena_url=?',(url_for('teams_duel',did=did),))
            db().execute('DELETE FROM arena_team_duels WHERE id=?',(did,))
            db().commit(); return redirect(url_for('teams_arena',modo=f"{data['size']}v{data['size']}"))
        if action=='accept' and (not team(data['team_a'])['ready'] or not team(data['team_b'])['ready']):
            db().rollback(); flash('Uma das equipes não está mais disponível.','error'); return redirect(url_for('teams_duel',did=did))
        db().execute("UPDATE arena_team_duels SET status=?,responded_at=CURRENT_TIMESTAMP WHERE id=? AND status='pending'",
                     ('accepted' if action=='accept' else 'refused',did))
        notify_duel(data,pid,f"{data['name_b']} {'aceitou o desafio' if action=='accept' else 'recusou: fugiu da batalha'}. "
                    + ('Joguem e enviem o ID somente ao terminar.' if action=='accept' else ''))
        db().commit(); return redirect(url_for('teams_duel',did=did))

    def match_reply(did,message,kind='error'):
        if request.accept_mimetypes.best=='application/json':
            refresh=kind in ('success','info')
            if refresh: flash(message,kind)
            return jsonify(message=message,ok=kind=='success',refresh=refresh,url=url_for('teams_duel',did=did))
        flash(message,kind); return redirect(url_for('teams_duel',did=did))

    @app.post('/arena/equipes/duelo/<int:did>/partida')
    @protected
    def teams_match(did):
        csrf(); pid=viewer_id(); data=duel(did)
        if pid not in {m['player_id'] for m in data['members']}: abort(403)
        if data['status'] not in ('accepted','match_pending'): return match_reply(did,'O desafio precisa ser aceito antes de informar o resultado.')
        mid=request.form.get('match_id',data['match_id']).strip().removeprefix('#')
        used=db().execute('SELECT * FROM arena_match_claims WHERE match_id=?',(mid,)).fetchone()
        if used and (used['queue']!='teams' or used['event_id']!=did): return match_reply(did,'Esse ID já foi usado em outro duelo.')
        expected=[{m['profile_id'] for m in data[side]} for side in ('a','b')]
        try: result=lookup_match(mid,set.union(*expected),expected_teams=expected)
        except ValueError as exc: return match_reply(did,str(exc))
        # Network lookup occurs before the write lock. Compare the snapshot again.
        db().execute('BEGIN IMMEDIATE')
        fresh=db().execute('SELECT * FROM arena_team_duels WHERE id=?',(did,)).fetchone()
        if not fresh or fresh['status'] not in ('accepted','match_pending') or fresh['match_id']!=data['match_id']:
            db().rollback(); return match_reply(did,'O duelo foi atualizado durante a consulta. Reabra a página para conferir.')
        completed=result['state']=='completed'
        side=None
        if completed:
            wins=set(result['winner_profile_ids']); losses=set(result['loser_profile_ids'])
            if not ((wins==expected[0] and losses==expected[1]) or (wins==expected[1] and losses==expected[0])):
                db().rollback(); return match_reply(did,'O resultado não corresponde aos elencos deste duelo.')
            side='a' if wins==expected[0] else 'b'
        try:
            db().execute('''UPDATE arena_team_duels SET match_id=?,match_url=?,match_error=?,match_payload=?,submitted_by=?,
              status=?,winner_side=?,finished_at=CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE '' END WHERE id=?''',
              (mid,result['match_url'],result.get('message',''),json.dumps(result,ensure_ascii=False),pid,
               'completed' if completed else 'match_pending',side,int(completed),did))
            if completed:
                winners=[m['player_id'] for m in data['members'] if m['side']==side]
                losers=[m['player_id'] for m in data['members'] if m['side']!=side]
                confirmed_at=db().execute('SELECT finished_at FROM arena_team_duels WHERE id=?',(did,)).fetchone()[0]
                arena_seasons.record_result(db(),f"{data['size']}v{data['size']}",did,winners,losers,confirmed_at)
                for m in data['members']:
                    notify(m['player_id'],pid,url_for('teams_duel',did=did),f"Resultado confirmado: {data['name_a'] if side=='a' else data['name_b']} venceu. Ranking atualizado.")
            elif mid!=data['match_id']:
                notify_duel(data,pid,f'Partida #{mid} informada. A consulta terminou e ainda aguarda confirmação do AoMStats.')
            db().commit()
        except sqlite3.IntegrityError:
            db().rollback(); return match_reply(did,'Esse ID acabou de ser registrado em outro duelo.')
        return match_reply(did,'Resultado confirmado e pontos registrados para todos os integrantes!' if completed else result['message'],
                           'success' if completed else 'info')

    @app.get('/arena/equipes/historico')
    def teams_history():
        pid=request.args.get('jogador',type=int); tid=request.args.get('equipe',type=int)
        where="d.status<>'cancelled'"; params=[]
        if pid: where+=' AND EXISTS(SELECT 1 FROM arena_duel_members m WHERE m.duel_id=d.id AND m.player_id=?)'; params.append(pid)
        if tid: where+=' AND (d.team_a=? OR d.team_b=?)'; params.extend((tid,tid))
        total=db().execute('SELECT COUNT(*) FROM arena_team_duels d WHERE '+where,params).fetchone()[0]
        pages=max(1,(total+19)//20); page=min(pages,max(1,request.args.get('pagina',1,type=int) or 1))
        rows=db().execute('SELECT d.* FROM arena_team_duels d WHERE '+where+' ORDER BY d.id DESC LIMIT 20 OFFSET ?',(*params,(page-1)*20)).fetchall()
        return render_template('arena_team_history.html',duels=rows,page=page,pages=pages,player_id=pid,team_id=tid)

    @lru_cache(maxsize=24)
    def cached_art(serialized,upload_dir,window):
        return render_team_card(json.loads(serialized),api['_load_social_avatar']).getvalue()

    @app.get('/midia/equipes/<token>.jpg')
    def teams_image(token):
        row=db().execute('SELECT id FROM arena_team_duels WHERE share_token=?',(token,)).fetchone()
        if not row: abort(404)
        data=duel(row['id'])
        content=cached_art(json.dumps(data,sort_keys=True,ensure_ascii=False),str(api['UPLOAD_DIR']),int(time.time()//300))
        return api['_public_card_response'](content,f"arena-{data['size']}x{data['size']}-{row['id']}.jpg")

    @app.get('/arena/temporadas')
    def arena_seasons_page():
        queue=request.args.get('modo','x1')
        if queue not in arena_seasons.QUEUES: queue='x1'
        selected=request.args.get('mes',arena_seasons.period())
        arena_seasons.close_seasons(db()); db().commit()
        months=[r['season'] for r in db().execute('SELECT season FROM arena_seasons ORDER BY season DESC LIMIT 36')]
        if arena_seasons.period() not in months: months.insert(0,arena_seasons.period())
        if selected not in months: selected=arena_seasons.period()
        rows=db().execute('''SELECT s.*,p.nickname,p.nickname_color,p.avatar_url,p.avatar_file,p.is_active
          FROM arena_standings s JOIN players p ON p.id=s.player_id
          WHERE s.season=? AND s.queue=? ORDER BY s.points DESC,s.wins DESC,s.losses,s.player_id''',(selected,queue)).fetchall()
        return render_template('arena_seasons.html',records=[dict(r,badge=arena_seasons.standing_badge(r)) for r in rows],
            season=selected,months=months,queue=queue,queues=arena_seasons.QUEUES,tiers=arena_seasons.TIERS,
            current=arena_seasons.period())

    def profile_progress(pid):
        data=arena_seasons.profile_seasons(db(),pid)
        data['team_games']=db().execute("""SELECT COUNT(*) FROM arena_duel_members m JOIN arena_team_duels d ON d.id=m.duel_id
          WHERE m.player_id=? AND d.status='completed'""",(pid,)).fetchone()[0]
        data['team_wins']=db().execute("""SELECT COUNT(*) FROM arena_duel_members m JOIN arena_team_duels d ON d.id=m.duel_id
          WHERE m.player_id=? AND d.status='completed' AND m.side=d.winner_side""",(pid,)).fetchone()[0]
        return data
    app.jinja_env.globals['arena_profile_progress']=profile_progress
    app.jinja_env.globals['arena_badge']=arena_seasons.badge
    app.jinja_env.globals['arena_outcome_points']=arena_rules.outcome_points
