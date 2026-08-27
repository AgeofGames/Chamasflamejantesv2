import os, sqlite3, uuid, re, urllib.request, html
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE=os.path.abspath(os.path.dirname(__file__))
DB=os.getenv('DATABASE_PATH',os.path.join(BASE,'database','chamas_flamejantes.sqlite'))
UPLOAD=os.path.join(BASE,'uploads')
app=Flask(__name__); app.secret_key=os.getenv('SECRET_KEY','change-this-on-railway-v11')
app.config.update(MAX_CONTENT_LENGTH=64*1024*1024,UPLOAD_FOLDER=UPLOAD)

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c
def init_db():
 os.makedirs(os.path.dirname(DB),exist_ok=True)
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,is_admin INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS players(id INTEGER PRIMARY KEY,nick TEXT NOT NULL,photo TEXT,aomstats TEXT UNIQUE,steam TEXT,discord TEXT,elo INTEGER,phrase TEXT,normal_wins INTEGER DEFAULT 0,normal_losses INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS tournaments(id INTEGER PRIMARY KEY,name TEXT NOT NULL,modality TEXT NOT NULL,prize_type TEXT DEFAULT 'Dinheiro',prize TEXT,event_date TEXT,max_entries INTEGER,status TEXT DEFAULT 'Fechado',rules TEXT,winner_text TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,member_names TEXT,eliminated INTEGER DEFAULT 0,FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE);
  CREATE TABLE IF NOT EXISTS tournament_players(tournament_id INTEGER,player_id INTEGER,team_name TEXT,PRIMARY KEY(tournament_id,player_id),FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE);
  CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,player1 TEXT,player2 TEXT,winner TEXT,round_name TEXT,played_at TEXT,FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE);
  CREATE TABLE IF NOT EXISTS sponsors(id INTEGER PRIMARY KEY,name TEXT NOT NULL,aomstats TEXT,photo TEXT,description TEXT,link TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS community_rank(id INTEGER PRIMARY KEY,player_id INTEGER UNIQUE,community_elo INTEGER,note TEXT,FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE);
  CREATE TABLE IF NOT EXISTS maps(id INTEGER PRIMARY KEY,name TEXT NOT NULL,creator TEXT,category TEXT,file_path TEXT,image_path TEXT,downloads INTEGER DEFAULT 0,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS duels(id INTEGER PRIMARY KEY,challenger_id INTEGER,challenged_id INTEGER,status TEXT DEFAULT 'Solicitado',winner_id INTEGER,requested_at TEXT DEFAULT CURRENT_TIMESTAMP,finished_at TEXT,FOREIGN KEY(challenger_id) REFERENCES players(id),FOREIGN KEY(challenged_id) REFERENCES players(id),FOREIGN KEY(winner_id) REFERENCES players(id));
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
  ''')
  c.execute('INSERT OR IGNORE INTO users(username,password_hash) VALUES(?,?)',('yukinochannyan',generate_password_hash('yukinochannyan60')))
  for k in ('whatsapp','discord','telegram'): c.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)',(k,''))
 print('🔥 CHAMAS FLAMEJANTES V11 CLEAN\nDATABASE: SQLITE\nSTATUS: READY',flush=True)

def admin_required(f):
 @wraps(f)
 def w(*a,**k):
  if not session.get('admin'): return redirect(url_for('login'))
  return f(*a,**k)
 return w
def save_file(f,folder,allowed):
 if not f or not f.filename:return None
 ext=f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else ''
 if ext not in allowed: raise ValueError('Formato de arquivo não permitido.')
 name=f'{uuid.uuid4().hex}_{secure_filename(f.filename)}'; path=os.path.join(UPLOAD,folder); os.makedirs(path,exist_ok=True); f.save(os.path.join(path,name)); return f'{folder}/{name}'
def avatar_from_url(url):
 if not url:return None
 m=re.search(r'https://avatars\.steamstatic\.com/[A-Za-z0-9_./-]+',url)
 return m.group(0) if m else None

def lookup_aomstats(url):
 if not re.match(r'^https://(?:www\.)?aomstats\.io/profile/\d+',url or ''): raise ValueError('Link do AoMStats inválido.')
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 ChamasFlamejantes/11','Accept':'text/html'})
 raw=urllib.request.urlopen(req,timeout=15).read().decode('utf-8','ignore')
 def meta(prop):
  m=re.search(r'<meta[^>]+property=["\']'+re.escape(prop)+r'["\'][^>]+content=["\']([^"\']+)',raw,re.I)
  return html.unescape(m.group(1)) if m else ''
 title=meta('og:title').replace(' - aomstats','').strip(); photo=meta('og:image'); desc=meta('og:description')
 rating=re.search(r'\((\d+) Elo\)',desc); record=re.search(r'(\d+)W-(\d+)L',desc)
 return {'nick':title,'photo':photo if 'avatars.steamstatic.com' in photo else '','elo':int(rating.group(1)) if rating else None,'wins':int(record.group(1)) if record else 0,'losses':int(record.group(2)) if record else 0,'profile':url}

@app.context_processor
def ctx():
 with db() as c: settings={r['key']:r['value'] for r in c.execute('SELECT * FROM settings')}
 return dict(settings=settings,admin=bool(session.get('admin')))
@app.route('/health')
def health():return jsonify(version='11-clean',database='ok')
@app.route('/api/aomstats')
def aomstats_lookup():
 try:return jsonify(ok=True,**lookup_aomstats(request.args.get('url','')))
 except Exception as e:return jsonify(ok=False,error='Não foi possível consultar o perfil agora. Confira o link ou preencha manualmente.'),422
@app.route('/')
def home():
 with db() as c:
  ts=c.execute("SELECT * FROM tournaments WHERE status='Aberto' ORDER BY event_date").fetchall(); champs=c.execute("SELECT * FROM tournaments WHERE status='Finalizado' AND winner_text IS NOT NULL ORDER BY id DESC LIMIT 4").fetchall(); ps=c.execute('SELECT * FROM sponsors ORDER BY id DESC LIMIT 6').fetchall()
 return render_template('home.html',page='home',tournaments=ts,champs=champs,sponsors=ps)
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  with db() as c:u=c.execute('SELECT * FROM users WHERE username=?',(request.form['username'],)).fetchone()
  if u and check_password_hash(u['password_hash'],request.form['password']):session['admin']=u['id'];return redirect(url_for('admin'))
  flash('Usuário ou senha inválidos.','error')
 return render_template('login.html',page='dark')
@app.route('/logout')
def logout():session.clear();return redirect('/')
@app.route('/tournaments')
def tournaments():
 with db() as c: rows=c.execute('SELECT * FROM tournaments ORDER BY CASE status WHEN "Aberto" THEN 0 WHEN "Fechado" THEN 1 ELSE 2 END,id DESC').fetchall()
 return render_template('listing.html',page='tournaments',title='TORNEIOS',kind='tournaments',rows=rows)
@app.route('/tournament/<int:i>',methods=['GET','POST'])
def tournament(i):
 with db() as c:
  t=c.execute('SELECT * FROM tournaments WHERE id=?',(i,)).fetchone()
  if not t:abort(404)
  if request.method=='POST':
   if t['status']!='Aberto':flash('Inscrições fechadas.','error');return redirect(request.url)
   f=request.files.get('photo'); photo=save_file(f,'profiles',{'jpg','jpeg','png','webp'}) if f and f.filename else avatar_from_url(request.form.get('photo_url')); nick=request.form['nick']; elo=None; wins=losses=0
   if not photo:
    try:
     found=lookup_aomstats(request.form['aomstats']);photo=found['photo'];nick=found['nick'] or nick;elo=found['elo'];wins=found['wins'];losses=found['losses']
    except Exception:pass
   cur=c.execute('INSERT OR IGNORE INTO players(nick,photo,aomstats,steam,discord,elo,normal_wins,normal_losses) VALUES(?,?,?,?,?,?,?,?)',(nick,photo,request.form['aomstats'],request.form.get('steam'),request.form['discord'],elo,wins,losses))
   p=c.execute('SELECT id FROM players WHERE aomstats=?',(request.form['aomstats'],)).fetchone(); c.execute('INSERT OR IGNORE INTO tournament_players VALUES(?,?,?)',(i,p['id'],request.form.get('team_name')));flash('Inscrição realizada!','ok')
  players=c.execute('SELECT p.*,tp.team_name FROM tournament_players tp JOIN players p ON p.id=tp.player_id WHERE tp.tournament_id=?',(i,)).fetchall(); matches=c.execute('SELECT * FROM matches WHERE tournament_id=? ORDER BY id DESC',(i,)).fetchall()
 return render_template('detail.html',page='tournaments',t=t,players=players,matches=matches)
@app.route('/elo')
def elo():
 with db() as c:rows=c.execute('''SELECT p.*,cr.community_elo,cr.note FROM community_rank cr JOIN players p ON p.id=cr.player_id ORDER BY cr.community_elo IS NULL,cr.community_elo DESC,p.nick''').fetchall()
 ranked=[x for x in rows if x['community_elo'] is not None]; best=ranked[0] if ranked else None; worst=ranked[-1] if ranked else None
 return render_template('listing.html',page='elo',title='ELO DA COMUNIDADE',kind='elo',rows=rows,best=best,worst=worst)
@app.route('/x1')
def x1():
 with db() as c:
  players=c.execute('''SELECT p.*,SUM(CASE WHEN d.winner_id=p.id AND d.status='Finalizado' THEN 1 ELSE 0 END) wins,SUM(CASE WHEN d.status='Finalizado' AND (d.challenger_id=p.id OR d.challenged_id=p.id) AND d.winner_id!=p.id THEN 1 ELSE 0 END) losses FROM players p LEFT JOIN duels d ON d.challenger_id=p.id OR d.challenged_id=p.id GROUP BY p.id ORDER BY wins DESC''').fetchall(); duels=c.execute('''SELECT d.*,a.nick challenger,b.nick challenged,w.nick winner FROM duels d JOIN players a ON a.id=d.challenger_id JOIN players b ON b.id=d.challenged_id LEFT JOIN players w ON w.id=d.winner_id ORDER BY d.id DESC''').fetchall()
 return render_template('listing.html',page='x1',title='DUELOS X1',kind='x1',rows=players,duels=duels)
@app.route('/challenge',methods=['POST'])
def challenge():
 a=int(request.form['challenger']);b=int(request.form['challenged'])
 if a==b:flash('Escolha jogadores diferentes.','error');return redirect('/x1')
 with db() as c:
  active=c.execute("SELECT 1 FROM duels WHERE status!='Finalizado' AND (challenger_id IN (?,?) OR challenged_id IN (?,?))",(a,b,a,b)).fetchone()
  if active:flash('Um dos jogadores já possui duelo ativo.','error')
  else:c.execute('INSERT INTO duels(challenger_id,challenged_id) VALUES(?,?)',(a,b));flash('Desafio solicitado!','ok')
 return redirect('/x1')
@app.route('/player/<int:i>')
def player(i):
 with db() as c:p=c.execute('SELECT * FROM players WHERE id=?',(i,)).fetchone();hist=c.execute('''SELECT d.*,a.nick challenger,b.nick challenged,w.nick winner FROM duels d JOIN players a ON a.id=d.challenger_id JOIN players b ON b.id=d.challenged_id LEFT JOIN players w ON w.id=d.winner_id WHERE d.challenger_id=? OR d.challenged_id=? ORDER BY d.id DESC''',(i,i)).fetchall()
 if not p:abort(404)
 return render_template('player.html',page='x1',p=p,hist=hist)
@app.route('/maps')
def maps():
 with db() as c:rows=c.execute('SELECT * FROM maps ORDER BY id DESC').fetchall()
 return render_template('listing.html',page='maps',title='BAIXAR MAPAS',kind='maps',rows=rows)
@app.route('/map/<int:i>/download')
def download_map(i):
 with db() as c:m=c.execute('SELECT * FROM maps WHERE id=?',(i,)).fetchone();c.execute('UPDATE maps SET downloads=downloads+1 WHERE id=?',(i,))
 if not m:abort(404)
 return send_from_directory(os.path.join(UPLOAD,'maps'),os.path.basename(m['file_path']),as_attachment=True)
@app.route('/sponsors')
def sponsors():
 with db() as c:rows=c.execute('SELECT * FROM sponsors ORDER BY id DESC').fetchall()
 return render_template('listing.html',page='sponsors',title='PATROCINADORES OFICIAIS',kind='sponsors',rows=rows)
@app.route('/uploads/<path:p>')
def uploads(p):return send_from_directory(UPLOAD,p)

@app.route('/admin',methods=['GET','POST'])
@admin_required
def admin():
 with db() as c:
  if request.method=='POST':
   action=request.form['action']
   try:
    if action=='tournament':c.execute('INSERT INTO tournaments(name,modality,prize_type,prize,event_date,max_entries,status,rules) VALUES(?,?,?,?,?,?,?,?)',tuple(request.form.get(x) for x in ('name','modality','prize_type','prize','event_date','max_entries','status','rules')))
    elif action=='match':c.execute('INSERT INTO matches(tournament_id,player1,player2,winner,round_name,played_at) VALUES(?,?,?,?,?,?)',(request.form['tournament_id'],request.form['player1'],request.form['player2'],request.form.get('winner'),request.form.get('round_name'),datetime.now().isoformat(timespec='minutes')))
    elif action=='finish_tournament':c.execute("UPDATE tournaments SET status='Finalizado',winner_text=? WHERE id=?",(request.form['winner_text'],request.form['tournament_id']))
    elif action=='player':
     photo=save_file(request.files.get('photo'),'profiles',{'jpg','jpeg','png','webp'}) or avatar_from_url(request.form.get('photo_url'));c.execute('INSERT INTO players(nick,photo,aomstats,steam,discord,elo,phrase,normal_wins,normal_losses) VALUES(?,?,?,?,?,?,?,?,?)',(request.form['nick'],photo,request.form.get('aomstats'),request.form.get('steam'),request.form.get('discord'),request.form.get('elo') or None,request.form.get('phrase'),request.form.get('normal_wins') or 0,request.form.get('normal_losses') or 0))
    elif action=='elo':c.execute('INSERT OR REPLACE INTO community_rank(player_id,community_elo,note) VALUES(?,?,?)',(request.form['player_id'],request.form.get('community_elo') or None,request.form.get('note')))
    elif action=='sponsor':
     photo=save_file(request.files.get('photo'),'sponsors',{'jpg','jpeg','png','webp'}) or avatar_from_url(request.form.get('photo_url'));c.execute('INSERT INTO sponsors(name,aomstats,photo,description,link) VALUES(?,?,?,?,?)',(request.form['name'],request.form.get('aomstats'),photo,request.form.get('description'),request.form.get('link')))
    elif action=='map':
     file=save_file(request.files['file'],'maps',{'zip','rar','7z'});image=save_file(request.files.get('image'),'maps',{'jpg','jpeg','png','webp'});c.execute('INSERT INTO maps(name,creator,category,file_path,image_path) VALUES(?,?,?,?,?)',(request.form['name'],request.form['creator'],request.form['category'],file,image))
    elif action=='duel':
     status=request.form['status']; winner=request.form.get('winner_id') or None;c.execute('UPDATE duels SET status=?,winner_id=?,finished_at=? WHERE id=?',(status,winner,datetime.now().isoformat(timespec='minutes') if status=='Finalizado' else None,request.form['duel_id']))
    elif action=='settings':
     for k in ('whatsapp','discord','telegram'):c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,request.form.get(k,'')))
    elif action=='password':
     if request.form['new_password']!=request.form['confirm']:raise ValueError('As senhas não coincidem.')
     c.execute('UPDATE users SET username=?,password_hash=? WHERE id=?',(request.form['username'],generate_password_hash(request.form['new_password']),session['admin']))
    flash('Salvo com sucesso.','ok')
   except (ValueError,sqlite3.Error) as e:flash(str(e),'error')
  ts=c.execute('SELECT * FROM tournaments ORDER BY id DESC').fetchall();ps=c.execute('SELECT * FROM players ORDER BY nick').fetchall();ds=c.execute('''SELECT d.*,a.nick challenger,b.nick challenged FROM duels d JOIN players a ON a.id=d.challenger_id JOIN players b ON b.id=d.challenged_id WHERE d.status!='Finalizado' ORDER BY d.id DESC''').fetchall()
 return render_template('admin.html',page='dark',tournaments=ts,players=ps,duels=ds)

init_db()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.getenv('PORT',5000)),debug=False)
