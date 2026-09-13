"""Player journey and replay discussion, backed by existing results."""
from collections import defaultdict
from datetime import datetime, timezone
import math
from flask import abort, flash, g, redirect, render_template, request, session, url_for
import arena_seasons

def current_account(api):
    if 'hub_account' not in g:g.hub_account=api['current_social_account']()
    return g.hub_account

def init_schema(db):
    # Retain legacy wall/note tables for upgrades; these features have no routes.
    # Existing replay comments share this schema and must remain intact.
    statements=[
      '''CREATE TABLE IF NOT EXISTS community_profile_settings(player_id INTEGER PRIMARY KEY REFERENCES players(id) ON DELETE CASCADE,cover_key TEXT NOT NULL DEFAULT 'chamas')''',
      '''CREATE TABLE IF NOT EXISTS community_build_notes(account_id INTEGER NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,build_id TEXT NOT NULL,favorite INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(account_id,build_id))''',
      '''CREATE TABLE IF NOT EXISTS community_posts(id INTEGER PRIMARY KEY AUTOINCREMENT,author_id INTEGER NOT NULL REFERENCES players(id),kind TEXT NOT NULL CHECK(kind IN ('estrategia','novidade','vitoria')),title TEXT NOT NULL,body TEXT NOT NULL DEFAULT '',queue TEXT,event_id INTEGER,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,edited_at TEXT NOT NULL DEFAULT '',deleted INTEGER NOT NULL DEFAULT 0)''',
      '''CREATE UNIQUE INDEX IF NOT EXISTS community_victory_once ON community_posts(author_id,queue,event_id) WHERE kind='vitoria' AND deleted=0''',
      '''CREATE INDEX IF NOT EXISTS community_posts_recent ON community_posts(deleted,id DESC)''',
      '''CREATE TABLE IF NOT EXISTS community_likes(post_id INTEGER NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,player_id INTEGER NOT NULL REFERENCES players(id),PRIMARY KEY(post_id,player_id))''',
      '''CREATE TABLE IF NOT EXISTS community_comments(id INTEGER PRIMARY KEY AUTOINCREMENT,author_id INTEGER NOT NULL REFERENCES players(id),post_id INTEGER REFERENCES community_posts(id) ON DELETE CASCADE,replay_id INTEGER REFERENCES arena_replays(id) ON DELETE CASCADE,body TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,deleted INTEGER NOT NULL DEFAULT 0,CHECK((post_id IS NOT NULL)+(replay_id IS NOT NULL)=1))''',
      'CREATE INDEX IF NOT EXISTS community_comments_post ON community_comments(post_id,deleted,id)',
      'CREATE INDEX IF NOT EXISTS community_comments_replay ON community_comments(replay_id,deleted,id)',
      'CREATE INDEX IF NOT EXISTS community_posts_author ON community_posts(author_id,created_at)',
      'CREATE INDEX IF NOT EXISTS community_comments_author ON community_comments(author_id,created_at)',
      'CREATE INDEX IF NOT EXISTS arena_results_profile_date ON arena_results(player_id,recorded_at)']
    for sql in statements:db.execute(sql)

def as_utc(value):
    try:
        date=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)
    except (ValueError,TypeError):return None

def local_date(value,short=False):
    date=as_utc(value)
    return date.astimezone(arena_seasons.ZONE).strftime('%d/%m %H:%M' if short else '%d/%m/%Y às %H:%M') if date else 'Data não informada'

def event_path(queue,event_id):
    return f'/duelo/{int(event_id)}' if queue=='x1' else f'/arena/equipes/duelo/{int(event_id)}'

def notify(db,pid,actor,path,message,kind='community_comment',duel_id=None):
    db.execute('''INSERT INTO social_notifications(account_id,actor_player_id,duel_id,kind,message,arena_url) SELECT id,?,?,?,?,? FROM social_accounts WHERE player_id=?''',(actor,duel_id,kind,message[:500],'' if duel_id else path,pid))

def read_notices(db,account_id,path):
    db.execute('UPDATE social_notifications SET is_read=1 WHERE account_id=? AND arena_url=?',(account_id,path));db.commit()

def profile_rivalries(db,pid):
    rows=db.execute('''SELECT d.*,p.id opponent_id,p.nickname,p.nickname_color,p.avatar_url,p.avatar_file,p.is_active FROM social_duels d JOIN players p ON p.id=CASE WHEN d.challenger_id=? THEN d.challenged_id ELSE d.challenger_id END WHERE d.status='completed' AND d.winner_id IS NOT NULL AND d.loser_id IS NOT NULL AND (d.challenger_id=? OR d.challenged_id=?) ORDER BY julianday(COALESCE(NULLIF(d.finished_at,''),d.requested_at)),d.id''',(pid,pid,pid)).fetchall()
    rivals={}
    for row in rows:
        oid=row['opponent_id']
        if oid not in rivals:
            rivals[oid]=dict(opponent={k:row[k] for k in ('nickname','nickname_color','avatar_url','avatar_file','is_active')},opponent_id=oid,wins=0,losses=0,best_self=0,best_opponent=0,run_self=0,run_opponent=0,last_self=None,last_opponent=None,history=[])
            rivals[oid]['opponent']['id']=oid
        r=rivals[oid];won=row['winner_id']==pid
        r['wins' if won else 'losses']+=1
        r['run_self']=r['run_self']+1 if won else 0;r['run_opponent']=0 if won else r['run_opponent']+1
        r['best_self']=max(r['best_self'],r['run_self']);r['best_opponent']=max(r['best_opponent'],r['run_opponent'])
        entry=dict(id=row['id'],won=won,match_id=row['match_id'],date=row['finished_at'] or row['requested_at'],winner_id=row['winner_id'],url=event_path('x1',row['id']))
        r['last_self' if won else 'last_opponent']=entry;r['last']=entry;r['history'].append(entry)
    return sorted(rivals.values(),key=lambda r:(-(r['wins']+r['losses']),-r['last']['id']))

def achievements(rows,rivals):
    first=streak=giant=None;runs=defaultdict(int);best=0
    for r in rows:
        won=bool(r['won'])
        if won and first is None:first=r
        runs[r['queue']]=runs[r['queue']]+1 if won else 0;best=max(best,runs[r['queue']])
        if runs[r['queue']]>=5 and streak is None:streak=r
        if won and r['rating_self'] is not None and r['rating_opponent'] is not None and r['rating_self']<r['rating_opponent'] and giant is None:giant=r
    minimum=datetime.min.replace(tzinfo=timezone.utc);maximum=datetime.max.replace(tzinfo=timezone.utc)
    legacy=sorted([e for r in rivals for e in r['history']],key=lambda e:(as_utc(e['date']) or minimum,e['id']))
    run=0
    for e in legacy:
        evidence=dict(recorded_at=e['date'],queue='x1',event_id=e['id']);run=run+1 if e['won'] else 0;best=max(best,run)
        if e['won'] and (first is None or (as_utc(e['date']) or maximum)<(as_utc(first['recorded_at']) or maximum)):first=evidence
        if run>=5 and (streak is None or (as_utc(e['date']) or maximum)<(as_utc(streak['recorded_at']) or maximum)):streak=evidence
    definitions=[('first','Primeira vitória','Vença um duelo confirmado na Arena.',first,1 if first else 0,1),('streak','Chama imparável','Vença cinco duelos seguidos na mesma modalidade.',streak,min(best,5),5),('giant','Caçador de gigantes','Vença um adversário de Elo maior, conforme o Elo registrado no duelo.',giant,1 if giant else 0,1)]
    return [dict(key=k,name=n,description=d,unlocked=bool(e),progress=p,goal=goal,date=e['recorded_at'] if e else None,url=event_path(e['queue'],e['event_id']) if e else '') for k,n,d,e,p,goal in definitions]

def evolution(rows,queue,month):
    events=[]
    for r in rows:
        if r['queue']!=queue or r['season']!=month:continue
        delta=r['points_delta'] if r['points_delta'] is not None else r['points_after']-r['points_before']
        events.append(dict(index=len(events)+1,won=bool(r['won']),date=local_date(r['recorded_at']),before=r['points_before'],after=r['points_after'],delta=delta,adjustment=max(0,abs(delta)-30)*(1 if delta>0 else -1),applied=r['points_after']-r['points_before'],url=event_path(queue,r['event_id']),event_id=r['event_id']))
    ceiling=max([30]+[e['after'] for e in events]+[e['before'] for e in events])
    values=([events[0]['before']]+[e['after'] for e in events]) if events else []
    coords=[dict(x=round(44+i*660/max(1,len(values)-1),2),y=round(204-v*170/ceiling,2),value=v) for i,v in enumerate(values)]
    for e,c in zip(events,coords[1:]):e.update(c)
    return dict(events=events,coordinates=coords,points=' '.join(f"{p['x']},{p['y']}" for p in coords),max_points=ceiling,final=values[-1] if values else 0,queue=queue,month=month)

def comments(db,kind,target_id,page=1):
    column='post_id' if kind=='post' else 'replay_id'
    total=db.execute(f'SELECT COUNT(*) FROM community_comments WHERE {column}=? AND deleted=0',(target_id,)).fetchone()[0]
    pages=max(1,math.ceil(total/30));page=min(max(1,page),pages)
    rows=db.execute(f'''SELECT c.*,p.nickname,p.nickname_color,p.avatar_url,p.avatar_file,p.is_active FROM community_comments c JOIN players p ON p.id=c.author_id WHERE c.{column}=? AND c.deleted=0 ORDER BY c.id LIMIT 30 OFFSET ?''',(target_id,(page-1)*30)).fetchall()
    return dict(items=[dict(r) for r in rows],total=total,page=page,pages=pages,kind=kind,target_id=target_id)

def install(app,api):
    def db():return api['get_db']()
    def account():return current_account(api)
    def pid():
        a=account();return a['player_id'] if a else None
    def player(player_id):
        row=api['get_social_player'](player_id)
        if not row:abort(404)
        return api['social_player_payload'](row)
    protected=api['social_profile_required']
    def covers():
        choices=[dict(key='chamas',name='Chamas Flamejantes',group='Comunidade',image='',color='#e95d20')]
        colors=['#71b8ff','#e4b867','#b7dded','#78cba0','#e39a87','#d9a0ed','#8edbc2']
        for i,(pantheon,names) in enumerate(api['knowledge_catalog']().get('gods',{}).items()):
            for name in names:
                slug=api['knowledge_image_name'](name)
                if (api['BASE_DIR']/'static'/'knowledge'/'gods'/f'{slug}.webp').is_file():choices.append(dict(key=slug,name=name,group=api['PANTHEON_META'].get(pantheon,{}).get('name',pantheon),image=url_for('static',filename=f'knowledge/gods/{slug}.webp'),color=colors[i%len(colors)]))
        return choices
    def profile_hub(player_id,compact=False):
        cache=g.setdefault('hub_profiles',{});key=(player_id,compact)
        if key in cache:return cache[key]
        rivals=profile_rivalries(db(),player_id)
        rows=[dict(r) for r in db().execute('SELECT * FROM arena_results WHERE player_id=? ORDER BY julianday(recorded_at),rowid',(player_id,))]
        months=sorted({r['season'] for r in rows}|{arena_seasons.period()},reverse=True)
        month=request.args.get('evo_mes',arena_seasons.period());month=month if month in months else arena_seasons.period()
        queue=request.args.get('evo_modo','x1');queue=queue if queue in arena_seasons.QUEUES else 'x1'
        setting=db().execute('SELECT cover_key FROM community_profile_settings WHERE player_id=?',(player_id,)).fetchone();choices=covers()
        data=dict(rivals=rivals,achievements=achievements(rows,rivals),cover=next((c for c in choices if setting and c['key']==setting['cover_key']),choices[0]),months=months,queues=arena_seasons.QUEUES,evolution=evolution(rows,queue,month) if not compact else None)
        cache[key]=data;return data
    app.jinja_env.globals['hub_profile']=profile_hub
    app.jinja_env.filters['br_date']=local_date

    @app.route('/meu-perfil/capa',methods=['GET','POST'])
    @protected
    def hub_cover():
        choices=covers()
        if request.method=='POST':
            api['require_csrf']();key=request.form.get('cover_key','')
            if key not in {c['key'] for c in choices}:abort(400,'Escolha uma das capas disponíveis.')
            db().execute('INSERT INTO community_profile_settings(player_id,cover_key) VALUES(?,?) ON CONFLICT(player_id) DO UPDATE SET cover_key=excluded.cover_key',(pid(),key));db().commit()
            flash('Sua capa foi atualizada.','success');return redirect(url_for('social_profile',player_id=pid()))
        return render_template('hub_covers.html',profile=player(pid()),choices=choices,selected=profile_hub(pid(),True)['cover']['key'])

    @app.get('/rivalidade/<int:player_a>/<int:player_b>')
    def hub_rivalry(player_a,player_b):
        if player_a==player_b:abort(404)
        a,b=player(player_a),player(player_b)
        rival=next((r for r in profile_rivalries(db(),player_a) if r['opponent_id']==player_b),None)
        if not rival:rival=dict(wins=0,losses=0,best_self=0,best_opponent=0,last_self=None,last_opponent=None,last=None,history=[])
        pages=max(1,math.ceil(len(rival['history'])/25));page=min(max(1,request.args.get('pagina',1,type=int) or 1),pages)
        return render_template('hub_rivalry.html',a=a,b=b,rival=rival,page=page,pages=pages,entries=list(reversed(rival['history']))[(page-1)*25:page*25])

    install_replay_comments(app,api,db,account,pid,protected)


def install_replay_comments(app,api,db,account,pid,protected):
    """The wall is retired. Only comments on completed duel replays remain public."""
    from duel_extras import event_info

    def replay_target(replay_id):
        row=db().execute('SELECT * FROM arena_replays WHERE id=? AND deleted=0',(replay_id,)).fetchone()
        e=event_info(db(),row['queue'],row['event_id']) if row else None
        if not e or e['status']!='completed':abort(404)
        return row['uploader_id'],url_for('hub_replay',replay_id=replay_id)

    @app.post('/comentar/replay/<int:target_id>')
    @protected
    def hub_comment(target_id):
        api['require_csrf']();author,path=replay_target(target_id);body=request.form.get('body','').strip()
        if not 1<=len(body)<=1500:abort(400,'Escreva um comentário de até 1.500 caracteres.')
        db().execute('BEGIN IMMEDIATE')
        count=db().execute("SELECT COUNT(*) FROM community_comments WHERE author_id=? AND created_at>=datetime('now','-60 seconds')",(pid(),)).fetchone()[0]
        if count>=10:abort(429,'Muitos envios em pouco tempo. Aguarde um pouco para comentar novamente.')
        cid=db().execute('INSERT INTO community_comments(author_id,replay_id,body) VALUES(?,?,?)',(pid(),target_id,body)).lastrowid
        if author!=pid():notify(db(),author,pid(),path,'Novo comentário no replay que você enviou.')
        total=db().execute('SELECT COUNT(*) FROM community_comments WHERE replay_id=? AND deleted=0',(target_id,)).fetchone()[0]
        db().commit();return redirect(path+f'?pagina={max(1,math.ceil(total/30))}#comentario-{cid}')

    @app.post('/comentario/<int:comment_id>/excluir')
    def hub_delete_comment(comment_id):
        api['require_csrf']()
        row=db().execute('SELECT * FROM community_comments WHERE id=? AND deleted=0 AND replay_id IS NOT NULL',(comment_id,)).fetchone()
        if not row:abort(404)
        if not session.get('admin_id') and pid()!=row['author_id']:abort(403)
        _,path=replay_target(row['replay_id'])
        db().execute('UPDATE community_comments SET deleted=1 WHERE id=?',(comment_id,));db().commit()
        return redirect(path+'#comentarios')
