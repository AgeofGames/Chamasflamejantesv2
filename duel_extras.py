"""Bilateral scheduling and participant-uploaded replays for completed Arena duels."""
from datetime import datetime,timedelta,timezone
import hashlib
import os
from pathlib import Path
import sqlite3
import threading
import uuid
from flask import abort,flash,redirect,render_template,request,send_file,session,url_for
from werkzeug.utils import secure_filename
import arena_seasons
from community_hub import as_utc,local_date,event_path,notify,read_notices,comments,current_account

REPLAY_MAX_BYTES=32*1024*1024

def now_utc():return datetime.now(timezone.utc)

def init_schema(db):
    for sql in [
      '''CREATE TABLE IF NOT EXISTS arena_schedules(id INTEGER PRIMARY KEY AUTOINCREMENT,queue TEXT NOT NULL,event_id INTEGER NOT NULL,proposed_by INTEGER NOT NULL REFERENCES players(id),confirmed_by INTEGER REFERENCES players(id),scheduled_at TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('proposed','confirmed','declined','cancelled')),version INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(queue,event_id))''',
      'CREATE INDEX IF NOT EXISTS arena_schedules_due ON arena_schedules(status,julianday(scheduled_at))',
      '''CREATE TABLE IF NOT EXISTS arena_schedule_events(id INTEGER PRIMARY KEY AUTOINCREMENT,schedule_id INTEGER NOT NULL REFERENCES arena_schedules(id),version INTEGER NOT NULL,action TEXT NOT NULL,actor_id INTEGER NOT NULL REFERENCES players(id),scheduled_at TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''',
      '''CREATE TABLE IF NOT EXISTS arena_schedule_reminders(schedule_id INTEGER NOT NULL REFERENCES arena_schedules(id),version INTEGER NOT NULL,stage TEXT NOT NULL,player_id INTEGER NOT NULL REFERENCES players(id),PRIMARY KEY(schedule_id,version,stage,player_id))''',
      '''CREATE TABLE IF NOT EXISTS arena_replays(id INTEGER PRIMARY KEY AUTOINCREMENT,queue TEXT NOT NULL,event_id INTEGER NOT NULL,uploader_id INTEGER NOT NULL REFERENCES players(id),filename TEXT NOT NULL UNIQUE,original_name TEXT NOT NULL,size_bytes INTEGER NOT NULL,sha256 TEXT NOT NULL,game_version TEXT NOT NULL DEFAULT '',description TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,deleted INTEGER NOT NULL DEFAULT 0)''',
      '''CREATE UNIQUE INDEX IF NOT EXISTS arena_replays_one_per_player ON arena_replays(queue,event_id,uploader_id) WHERE deleted=0''',
      '''CREATE UNIQUE INDEX IF NOT EXISTS arena_replays_same_file ON arena_replays(queue,event_id,sha256) WHERE deleted=0''',
      'CREATE INDEX IF NOT EXISTS arena_replays_event ON arena_replays(queue,event_id,deleted)']:db.execute(sql)

def event_info(db,queue,event_id):
    if queue not in arena_seasons.QUEUES or not event_id:return None
    if queue=='x1':
        r=db.execute('''SELECT d.*,a.nickname name_a,b.nickname name_b FROM social_duels d JOIN players a ON a.id=d.challenger_id JOIN players b ON b.id=d.challenged_id WHERE d.id=?''',(event_id,)).fetchone()
        if not r or r['status']=='cancelled':return None
        data=dict(r);data.update(participants={r['challenger_id'],r['challenged_id']},controllers={r['challenger_id'],r['challenged_id']},winners={r['winner_id']} if r['winner_id'] else set())
        win_a=r['winner_id']==r['challenger_id']
    else:
        r=db.execute('SELECT * FROM arena_team_duels WHERE id=? AND size=?',(event_id,2 if queue=='2v2' else 3)).fetchone()
        if not r or r['status']=='cancelled':return None
        roster=db.execute('SELECT player_id,side FROM arena_duel_members WHERE duel_id=?',(event_id,)).fetchall();data=dict(r)
        data.update(participants={m['player_id'] for m in roster},controllers={r['captain_a'],r['captain_b']},winners={m['player_id'] for m in roster if m['side']==r['winner_side']})
        win_a=r['winner_side']=='a'
    winner,loser=(r['name_a'],r['name_b']) if win_a else (r['name_b'],r['name_a'])
    data['queue']=queue;data['url']=event_path(queue,event_id)
    data['title']=(f'{winner} venceu {loser}' if r['status']=='completed' else f"{r['name_a']} × {r['name_b']}")+' · '+arena_seasons.QUEUES[queue]
    return data

def event_image(e):
    return url_for('arena_share_image',share_token=e['share_token']) if e['queue']=='x1' else url_for('teams_image',token=e['share_token'])

def clear_schedule_notices(db,e):
    if e['queue']=='x1':db.execute("DELETE FROM social_notifications WHERE duel_id=? AND kind LIKE 'schedule_%'",(e['id'],))
    else:db.execute("DELETE FROM social_notifications WHERE arena_url=? AND kind LIKE 'schedule_%'",(e['url'],))

def schedule_notify(db,e,actor,message,kind):
    for pid in sorted(e['participants']):
        if pid!=actor:notify(db,pid,actor,e['url'],message,kind,e['id'] if e['queue']=='x1' else None)

def process_reminders(db,now=None):
    now=now or now_utc();params=((now-timedelta(minutes=15)).isoformat(),(now+timedelta(minutes=15)).isoformat())
    condition="status='confirmed' AND julianday(scheduled_at) BETWEEN julianday(?) AND julianday(?)"
    if not db.execute('SELECT 1 FROM arena_schedules WHERE '+condition+' LIMIT 1',params).fetchone():return 0
    db.execute('BEGIN IMMEDIATE');sent=0
    try:
        for r in db.execute('SELECT * FROM arena_schedules WHERE '+condition,params).fetchall():
            e=event_info(db,r['queue'],r['event_id'])
            if not e or e['status'] not in ('accepted','match_pending'):continue
            stage='soon' if as_utc(r['scheduled_at'])>now else 'start'
            message=('Duelo em breve' if stage=='soon' else 'Horário do duelo')+f": {e['title']}. Horário: {local_date(r['scheduled_at'])} (Brasília)."
            for pid in sorted(e['participants']):
                inserted=db.execute('INSERT OR IGNORE INTO arena_schedule_reminders VALUES(?,?,?,?)',(r['id'],r['version'],stage,pid)).rowcount
                if inserted:notify(db,pid,None,e['url'],message,'schedule_reminder',e['id'] if r['queue']=='x1' else None);sent+=1
        db.commit()
    except Exception:db.rollback();raise
    return sent

def start_reminder_worker(app,api):
    if os.environ.get('ARENA_REMINDERS_ENABLED','1').lower() in ('0','false','no'):return
    stop=threading.Event()
    def worker():
        while not stop.wait(20):
            if app.config.get('TESTING'):continue
            try:
                with app.app_context():process_reminders(api['get_db']())
            except sqlite3.Error:app.logger.warning('Lembretes da Arena: banco indisponível; nova tentativa no próximo ciclo.')
    app.extensions['arena_reminders_stop']=stop
    threading.Thread(target=worker,name='arena-reminders',daemon=True).start()

def install(app,api):
    def db():return api['get_db']()
    def account():return current_account(api)
    def pid():
        a=account();return a['player_id'] if a else None
    protected=api['social_profile_required']
    def event(queue,event_id):
        e=event_info(db(),queue,event_id)
        if not e:abort(404)
        return e
    def replay_dir():
        folder=Path(api['DB_PATH']).parent/'arena_replays';folder.mkdir(parents=True,exist_ok=True);return folder
    def replay_row(replay_id):
        r=db().execute('''SELECT r.*,p.nickname,p.nickname_color,p.avatar_url,p.avatar_file,p.is_active FROM arena_replays r JOIN players p ON p.id=r.uploader_id WHERE r.id=? AND r.deleted=0''',(replay_id,)).fetchone()
        if not r:abort(404)
        e=event(r['queue'],r['event_id'])
        if e['status']!='completed':abort(404)
        return dict(r),e
    def extras(queue,event_id):
        e=event(queue,event_id);s=db().execute('SELECT * FROM arena_schedules WHERE queue=? AND event_id=?',(queue,event_id)).fetchone()
        replays=[dict(r) for r in db().execute('''SELECT r.*,p.nickname,(SELECT COUNT(*) FROM community_comments c WHERE c.replay_id=r.id AND c.deleted=0) comment_count FROM arena_replays r JOIN players p ON p.id=r.uploader_id WHERE r.queue=? AND r.event_id=? AND r.deleted=0 ORDER BY r.id''',(queue,event_id))]
        return dict(event=e,schedule=dict(s) if s else None,replays=replays,controller=pid() in e['controllers'],participant=pid() in e['participants'],uploaded=any(r['uploader_id']==pid() for r in replays),replay_limit_mb=REPLAY_MAX_BYTES//1048576)
    app.jinja_env.globals['hub_duel_extras']=extras
    @app.get('/minha-agenda')
    @protected
    def hub_agenda():
        rows=db().execute("SELECT * FROM arena_schedules WHERE status IN ('proposed','confirmed') AND julianday(scheduled_at)>=julianday(?) ORDER BY julianday(scheduled_at)",((now_utc()-timedelta(hours=2)).isoformat(),)).fetchall();items=[]
        for r in rows:
            e=event_info(db(),r['queue'],r['event_id'])
            if e and pid() in e['participants'] and e['status'] in ('accepted','match_pending'):items.append(dict(r,event=e))
        return render_template('hub_agenda.html',items=items)
    @app.post('/agenda/<queue>/<int:event_id>/propor')
    @protected
    def hub_schedule_propose(queue,event_id):
        api['require_csrf']();raw=request.form.get('when','')
        try:
            if len(raw)!=16:raise ValueError
            when=datetime.strptime(raw,'%Y-%m-%dT%H:%M').replace(tzinfo=arena_seasons.ZONE).astimezone(timezone.utc)
        except ValueError:abort(400,'Informe uma data e horário válidos em Brasília.')
        if not now_utc()+timedelta(minutes=5)<=when<=now_utc()+timedelta(days=90):abort(400,'Escolha um horário entre cinco minutos e 90 dias a partir de agora.')
        db().execute('BEGIN IMMEDIATE');e=event(queue,event_id)
        if pid() not in e['controllers']:abort(403,'Somente os dois jogadores ou capitães podem combinar o horário.')
        if e['status'] not in ('accepted','match_pending') or e['match_id']:abort(409,'Combine o horário depois de aceitar e antes de informar o ID da partida.')
        current=db().execute('SELECT * FROM arena_schedules WHERE queue=? AND event_id=?',(queue,event_id)).fetchone()
        if request.form.get('version',0,type=int)!=(current['version'] if current else 0):abort(409,'O horário mudou. Abra o duelo novamente antes de propor outro horário.')
        if current:
            sid=current['id'];version=current['version']+1
            db().execute("UPDATE arena_schedules SET proposed_by=?,confirmed_by=NULL,scheduled_at=?,status='proposed',version=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(pid(),when.isoformat(),version,sid))
        else:version=1;sid=db().execute("INSERT INTO arena_schedules(queue,event_id,proposed_by,scheduled_at,status) VALUES(?,?,?,?,'proposed')",(queue,event_id,pid(),when.isoformat())).lastrowid
        db().execute('INSERT INTO arena_schedule_events(schedule_id,version,action,actor_id,scheduled_at) VALUES(?,?,?,?,?)',(sid,version,'proposed',pid(),when.isoformat()))
        clear_schedule_notices(db(),e);schedule_notify(db(),e,pid(),f'Proposta de horário: {local_date(when.isoformat())} (Brasília). Abra o duelo para aceitar ou sugerir outro horário.','schedule_proposed')
        db().commit();return redirect(e['url']+'#agendamento')
    @app.post('/agenda/<queue>/<int:event_id>/responder')
    @protected
    def hub_schedule_answer(queue,event_id):
        api['require_csrf']();db().execute('BEGIN IMMEDIATE');e=event(queue,event_id)
        if pid() not in e['controllers']:abort(403)
        r=db().execute('SELECT * FROM arena_schedules WHERE queue=? AND event_id=?',(queue,event_id)).fetchone()
        if not r:abort(404)
        if request.form.get('version',type=int)!=r['version']:abort(409,'Essa proposta mudou. Atualize a conversa.')
        if e['status'] not in ('accepted','match_pending') or e['match_id']:abort(409,'Este duelo não aceita mais alterações de horário.')
        answer=request.form.get('answer')
        if answer in ('accept','decline'):
            if r['status']!='proposed' or r['proposed_by']==pid():abort(403,'A resposta deve ser do adversário que recebeu a proposta.')
            if as_utc(r['scheduled_at'])<=now_utc():abort(409,'O horário passou. Sugira outro horário.')
            state='confirmed' if answer=='accept' else 'declined'
        elif answer=='cancel':
            if r['status'] not in ('proposed','confirmed'):abort(409)
            state='cancelled'
        else:abort(400)
        db().execute('UPDATE arena_schedules SET status=?,confirmed_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(state,pid() if state=='confirmed' else None,r['id']))
        db().execute('INSERT INTO arena_schedule_events(schedule_id,version,action,actor_id,scheduled_at) VALUES(?,?,?,?,?)',(r['id'],r['version'],state,pid(),r['scheduled_at']))
        clear_schedule_notices(db(),e);label={'confirmed':'Horário confirmado','declined':'Proposta de horário recusada','cancelled':'Agendamento cancelado'}[state]
        schedule_notify(db(),e,pid(),f'{label}: {local_date(r["scheduled_at"])} (Brasília).','schedule_'+state)
        db().commit();return redirect(e['url']+'#agendamento')
    @app.before_request
    def limit_replay_request():
        if request.endpoint=='hub_upload_replay' and request.content_length and request.content_length>REPLAY_MAX_BYTES+1048576:abort(413,'O replay deve ter até 32 MB.')
    @app.post('/replay/<queue>/<int:event_id>/enviar')
    @protected
    def hub_upload_replay(queue,event_id):
        api['require_csrf']();e=event(queue,event_id)
        if pid() not in e['participants']:abort(403,'Somente os participantes podem anexar o replay.')
        if e['status']!='completed':abort(409,'Confirme o resultado antes de enviar o replay.')
        upload=request.files.get('replay')
        if not upload or Path(upload.filename or '').suffix.lower()!='.mythrec':abort(400,'Envie o replay .mythrec do Age of Mythology: Retold.')
        description=request.form.get('description','').strip();version=request.form.get('game_version','').strip()
        if len(description)>1000 or len(version)>60:abort(400,'Use até 1.000 caracteres na descrição e 60 na versão do jogo.')
        filename=uuid.uuid4().hex+'.mythrec'
        try:path=replay_dir()/filename
        except OSError:abort(503,'Não foi possível guardar o replay agora. Tente novamente em instantes.')
        total=0;digest=hashlib.sha256();kept=False
        try:
            with path.open('xb') as destination:
                while True:
                    chunk=upload.stream.read(65536)
                    if not chunk:break
                    total+=len(chunk)
                    if total>REPLAY_MAX_BYTES:abort(413,'O replay deve ter até 32 MB.')
                    digest.update(chunk);destination.write(chunk)
            if total<64:abort(400,'O arquivo está vazio ou incompleto.')
            db().execute('BEGIN IMMEDIATE');e=event(queue,event_id)
            if e['status']!='completed' or pid() not in e['participants']:abort(409)
            duplicate=db().execute('SELECT id FROM arena_replays WHERE queue=? AND event_id=? AND sha256=? AND deleted=0',(queue,event_id,digest.hexdigest())).fetchone()
            if duplicate:db().rollback();flash('Esse replay já está disponível neste duelo.','success');return redirect(url_for('hub_replay',replay_id=duplicate['id']))
            if db().execute('SELECT 1 FROM arena_replays WHERE queue=? AND event_id=? AND uploader_id=? AND deleted=0',(queue,event_id,pid())).fetchone():abort(409,'Remova seu replay anterior para enviar outro neste duelo.')
            original=(Path(secure_filename(Path(upload.filename.replace('\\','/')).name)).stem or 'partida')[:160]+'.mythrec'
            rid=db().execute('''INSERT INTO arena_replays(queue,event_id,uploader_id,filename,original_name,size_bytes,sha256,game_version,description) VALUES(?,?,?,?,?,?,?,?,?)''',(queue,event_id,pid(),filename,original,total,digest.hexdigest(),version,description)).lastrowid
            db().commit();kept=True;return redirect(url_for('hub_replay',replay_id=rid))
        except OSError:db().rollback();abort(503,'Não foi possível guardar o replay agora. Tente novamente em instantes.')
        finally:
            if not kept:
                try:path.unlink(missing_ok=True)
                except OSError:app.logger.warning('Não foi possível remover um replay incompleto.')
    @app.get('/replays/<int:replay_id>')
    def hub_replay(replay_id):
        replay,e=replay_row(replay_id)
        if account():read_notices(db(),account()['account_id'],url_for('hub_replay',replay_id=replay_id))
        return render_template('hub_replay.html',replay=replay,event=e,can_remove=bool(session.get('admin_id') or pid()==replay['uploader_id']),discussion=comments(db(),'replay',replay_id,request.args.get('pagina',1,type=int) or 1))
    @app.get('/replays/<int:replay_id>/baixar')
    def hub_download_replay(replay_id):
        replay,_=replay_row(replay_id);folder=replay_dir();path=folder/replay['filename']
        if path.parent.resolve()!=folder.resolve() or not path.is_file():abort(404)
        response=send_file(path,mimetype='application/octet-stream',as_attachment=True,download_name=replay['original_name'],conditional=True)
        response.headers['X-Content-Type-Options']='nosniff';response.headers['Content-Security-Policy']="default-src 'none'; sandbox";return response
    @app.post('/replays/<int:replay_id>/excluir')
    def hub_remove_replay(replay_id):
        api['require_csrf']();replay,e=replay_row(replay_id)
        if not session.get('admin_id') and pid()!=replay['uploader_id']:abort(403)
        db().execute('UPDATE arena_replays SET deleted=1 WHERE id=?',(replay_id,));db().execute('DELETE FROM social_notifications WHERE arena_url=?',(url_for('hub_replay',replay_id=replay_id),));db().commit()
        try:(replay_dir()/replay['filename']).unlink(missing_ok=True)
        except OSError:app.logger.warning('Replay removido da página; arquivo aguarda limpeza no volume.')
        flash('Replay removido.','success');return redirect(e['url']+'#replays')
