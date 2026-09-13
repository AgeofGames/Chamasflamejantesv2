"""Search metadata and public discovery, with no external indexing requests."""
from datetime import datetime, timezone
import os
import re
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from flask import abort, flash, g, redirect, render_template, request, url_for
from jinja2 import pass_context
from markupsafe import Markup

INDEX = 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
NOINDEX = 'noindex, follow'
PRIVATE = 'noindex, nofollow'
SITEMAP_LIMIT = 45000
XMLNS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
PUBLIC_PAGES = {
    'home', 'open_tournaments_page', 'tournament_history', 'tournament_page',
    'tournament_participants', 'tournament_matches', 'tournament_result',
    'community_page', 'x1_page', 'social_duel_history', 'social_profile',
    'social_duel', 'social_duel_invite_share', 'social_duel_result_share',
    'teams_arena', 'teams_history', 'teams_profile', 'teams_duel',
    'arena_seasons_page', 'maps_page', 'programs_page', 'knowledge_page',
    'knowledge_build_orders_page', 'knowledge_god_page', 'knowledge_build_page',
    'hotkeys_guide_page', 'counter_guide_page', 'feedback_page', 'hub_rivalry',
    'hub_replay', 'site_directory',
}
SECTION_COPY = {
    'home': ('Chamas Flamejantes | Age of Mythology: Retold',
             'Comunidade brasileira de Age of Mythology: Retold com build orders em português, torneios, mapas e Arena X1, duplas e trios.'),
    'open_tournaments_page': ('Torneios de Age of Mythology: Retold',
             'Confira torneios de Age of Mythology: Retold, inscrições, horários, participantes e confrontos nas modalidades FFA, 1x1, 2x2 e MD3.'),
    'tournament_history': ('Histórico e campeões dos torneios de AoM Retold',
             'Veja os torneios encerrados de Age of Mythology: Retold, seus campeões, resultados e confrontos na comunidade Chamas Flamejantes.'),
    'community_page': ('Elo da Comunidade | Ranking de AoM Retold',
             'Conheça os jogadores de Age of Mythology: Retold, consulte o Elo da Comunidade e abra os perfis para ver seus dados e histórico.'),
    'x1_page': ('Arena X1 | Ranking e duelos de AoM Retold',
             'Desafie jogadores no Age of Mythology: Retold, acompanhe o ranking mensal X1, os emblemas e os resultados confirmados pelo AoMStats.'),
    'social_duel_history': ('Histórico de duelos X1 de AoM Retold',
             'Consulte partidas da Arena X1, vencedores, adversários e IDs confirmados. Filtre vitórias, derrotas, fugas e desafios ativos.'),
    'teams_history': ('Histórico de duplas e trios de AoM Retold',
             'Acompanhe o histórico público dos confrontos de duplas e trios, equipes, IDs das partidas e resultados na Arena Chamas Flamejantes.'),
    'maps_page': ('Mapas de Age of Mythology: Retold para baixar',
             'Encontre mapas de Age of Mythology: Retold por modalidade, consulte imagens e descrições e baixe os arquivos disponíveis na comunidade.'),
    'programs_page': ('Programas para Age of Mythology: Retold',
             'Conheça os programas disponibilizados pela comunidade Chamas Flamejantes, consulte suas descrições e acesse os downloads para AoM Retold.'),
    'knowledge_page': ('Guias de Age of Mythology: Retold em português',
             'Aprenda Age of Mythology: Retold com build orders, guia de counters e teclado interativo. Explore estratégias por deus e panteão.'),
    'knowledge_build_orders_page': ('Build orders de Age of Mythology: Retold',
             'Escolha build orders em português por deus e panteão. Consulte aberturas de economia, rush e água, com passos organizados por idade.'),
    'hotkeys_guide_page': ('Guia de teclas e atalhos de AoM Retold',
             'Consulte o teclado interativo de Age of Mythology: Retold: atalhos de unidades, construções, seleção, câmera e comandos por panteão.'),
    'counter_guide_page': ('Guia de counters de Age of Mythology: Retold',
             'Veja como responder às unidades de Age of Mythology: Retold. Consulte vantagens de combate e counters para adaptar seu exército.'),
    'feedback_page': ('Enviar feedback ao Chamas Flamejantes',
             'Envie sugestões ou relate um problema nos torneios, perfis, Arena, mapas e guias de Age of Mythology: Retold do Chamas Flamejantes.'),
    'site_directory': ('Mapa do site | Guias, torneios e Arena',
             'Encontre as páginas do Chamas Flamejantes: build orders por deus, guias de AoM Retold, mapas, programas, torneios e Arena da comunidade.'),
}
STATIC_DISCOVERY = [
    ('home', 'Início'), ('open_tournaments_page', 'Torneios'),
    ('tournament_history', 'Histórico de torneios'), ('community_page', 'Elo da Comunidade'),
    ('x1_page', 'Arena X1'), ('social_duel_history', 'Histórico X1'),
    ('teams_arena', 'Arena de duplas'), ('teams_history', 'Histórico de equipes'),
    ('arena_seasons_page', 'Temporadas e emblemas'), ('maps_page', 'Mapas'),
    ('programs_page', 'Programas'), ('knowledge_page', 'Conhecimento'),
    ('knowledge_build_orders_page', 'Build orders'), ('hotkeys_guide_page', 'Guia de teclas'),
    ('counter_guide_page', 'Guia de counters'), ('feedback_page', 'Feedback'),
    ('site_directory', 'Mapa do site'),
]


def plain(value, limit=0):
    text = ' '.join(str(Markup(str(value or '')).striptags()).split())
    if limit and len(text) > limit:
        text = text[:limit - 1].rsplit(' ', 1)[0].rstrip(' ,;:.') + '…'
    return text


def field(value, key, default=''):
    try:
        result = value[key]
        return default if result is None else result
    except (KeyError, TypeError, IndexError):
        return default


def modified(value):
    """Only emit known, valid, non-future dates; never use the request time."""
    if not value:
        return None
    try:
        date = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        if date > datetime.now(timezone.utc):
            return None
        return date.astimezone(timezone.utc).isoformat(timespec='seconds')
    except (ValueError, TypeError):
        return None


def install_seo(app, api):
    def origin():
        return api['PUBLIC_BASE_URL'].rstrip('/')

    def absolute(endpoint, **values):
        return origin() + url_for(endpoint, **values)

    def verification():
        supplied = os.environ.get('GOOGLE_SITE_VERIFICATION', '').strip()
        if supplied:
            return supplied if re.fullmatch(r'[A-Za-z0-9_-]{10,256}', supplied) else ''
        row = api['get_db']().execute("SELECT value FROM site_meta WHERE key='google_site_verification'").fetchone()
        return row['value'] if row and re.fullmatch(r'[A-Za-z0-9_-]{10,256}', row['value']) else ''

    @pass_context
    def page_metadata(context, old_title='', old_description=''):
        ep = request.endpoint or ''
        values = dict(request.view_args or {})
        canonical = absolute(ep, **values) if ep in PUBLIC_PAGES else None
        title, description = SECTION_COPY.get(ep, (plain(old_title), plain(old_description)))
        name = plain(field(context.get('site'), 'title', 'Chamas Flamejantes'))
        indexed = ep in PUBLIC_PAGES and not context.get('error_code')
        query = {}
        crumbs = [{'name': 'Início', 'url': absolute('home')}]
        label = title.split(' | ')[0].split(' • ')[0]
        profile, duel, team = context.get('profile'), context.get('duel'), context.get('team')
        tournament, build = context.get('tournament'), context.get('build')
        history = context.get('history')

        if ep.startswith('knowledge_') or ep in ('hotkeys_guide_page', 'counter_guide_page'):
            if ep != 'knowledge_page':
                crumbs.append({'name': 'Conhecimento', 'url': absolute('knowledge_page')})
            if ep in ('knowledge_god_page', 'knowledge_build_page'):
                crumbs.append({'name': 'Build orders', 'url': absolute('knowledge_build_orders_page')})
                god = plain(context.get('god_name') or field(build, 'god'))
                if ep == 'knowledge_god_page':
                    title = f'Build orders de {god} | Age of Mythology: Retold'
                    description = f'Explore {len(context.get("builds", []))} build orders de {god} em português para Age of Mythology: Retold, com passos de economia e avanço de idade.'
                    label = f'Build orders de {god}'
                else:
                    title = f'{plain(field(build, "title"))} — {god} | AoM Retold'
                    description = f'{plain(field(build, "title"))}: build order de {god} no Age of Mythology: Retold. {plain(field(build, "objective"))}'
                    label = plain(field(build, 'title'))
                    crumbs.append({'name': god, 'url': absolute('knowledge_god_page', god_slug=context['god_slug'])})

        if ep in ('tournament_page', 'tournament_participants', 'tournament_matches', 'tournament_result'):
            tname = plain(field(tournament, 'name'))
            sub = {'tournament_page': 'Torneio', 'tournament_participants': 'Participantes',
                   'tournament_matches': 'Confrontos', 'tournament_result': 'Resultado'}[ep]
            title = f'{sub}: {tname} | AoM Retold'
            description = f'{sub} de {tname} no Age of Mythology: Retold. ' + {
                'tournament_page': plain(field(tournament, 'description')) or 'Consulte a modalidade, inscrições, regras, horários e acompanhe as partidas.',
                'tournament_participants': 'Veja os jogadores e equipes inscritos, seus perfis e os dados da competição.',
                'tournament_matches': 'Acompanhe a tabela, as séries e os placares dos confrontos da competição.',
                'tournament_result': 'Confira os vencedores e a classificação final da competição.',
            }[ep]
            crumbs.append({'name': 'Torneios', 'url': absolute('open_tournaments_page')})
            if ep != 'tournament_page':
                crumbs.append({'name': tname, 'url': absolute('tournament_page', slug=values['slug'])})
            label = tname if ep == 'tournament_page' else sub
            indexed = indexed and bool(field(tournament, 'is_public', False))
            if ep == 'tournament_result' and field(tournament, 'status') != 'finalizado' and not context.get('winners'):
                indexed = False

        if ep in ('social_profile', 'social_duel_history') and profile:
            nickname = plain(field(profile, 'nickname'))
            stats = field(profile, 'stats', {})
            title = f'{nickname} | Perfil e histórico na Arena X1' if ep == 'social_profile' else f'Histórico X1 de {nickname}'
            description = f'{nickname} na Arena de Age of Mythology: Retold: {field(stats,"wins",0)} vitórias, {field(stats,"losses",0)} derrotas. Veja adversários, partidas, emblemas e evolução.'
            label = nickname if ep == 'social_profile' else f'Histórico de {nickname}'

        if ep in ('social_duel', 'social_duel_invite_share', 'social_duel_result_share') and duel:
            completed = field(duel, 'status') == 'completed'
            a = plain(field(field(duel, 'challenger'), 'nickname'))
            b = plain(field(field(duel, 'challenged'), 'nickname'))
            match = plain(field(duel, 'match_id'))
            title = f'{a} × {b} | Duelo X1 #{field(duel,"id")}'
            if completed:
                title = f'{plain(field(field(duel,"winner"),"nickname"))} venceu {plain(field(field(duel,"loser"),"nickname"))} | Partida {match or field(duel,"id")}'
            description = f'{a} contra {b} no Age of Mythology: Retold. ' + (f'Resultado confirmado da partida {match}. Veja vencedor, pontos e histórico do duelo.' if completed else 'Acompanhe o desafio público da Arena X1.')
            indexed = indexed and completed
            canonical = absolute('social_duel_result_share', share_token=field(duel, 'share_token')) if completed else absolute('social_duel', duel_id=field(duel, 'id'))
            label = f'Partida {match}' if match else f'Duelo #{field(duel,"id")}'

        if ep == 'teams_arena':
            size = context.get('size', 2)
            title = f'Arena {size}x{size} | {"Duplas" if size == 2 else "Trios"} de AoM Retold'
            description = f'Forme {"uma dupla" if size == 2 else "um trio"} para Age of Mythology: Retold, convide parceiros e desafie outras equipes. Veja o ranking mensal {size}x{size}.'
            label = f'Arena {size}×{size}'
            if size == 3:
                query['modo'] = '3v3'
        if ep == 'teams_profile' and team:
            size = field(team, 'size', 2)
            title = f'{plain(field(team,"name"))} | Equipe {size}x{size} de AoM Retold'
            description = f'Conheça {plain(field(team,"name"))}, equipe {size}x{size} na Arena de Age of Mythology: Retold. Veja integrantes, desafios e histórico de partidas.'
            label = plain(field(team, 'name'))
            indexed = indexed and not field(team, 'archived', 0) and bool(field(team, 'ready', False))
        if ep == 'teams_duel' and duel:
            title = f'{plain(field(duel,"title"))} | Duelo de equipes #{field(duel,"id")}'
            description = f'{plain(field(duel,"title"))} no Age of Mythology: Retold. Consulte os integrantes, o ID da partida e o resultado confirmado da Arena.'
            indexed = indexed and field(duel, 'status') == 'completed'
            label = f'Duelo de equipes #{field(duel,"id")}'
        if ep == 'arena_seasons_page':
            queue, season = context.get('queue', 'x1'), context.get('season', '')
            mode = {'x1':'X1','2v2':'2x2','3v3':'3x3'}.get(queue, 'X1')
            month = f'{season[5:]}/{season[:4]}'
            title = f'Ranking {mode} e emblemas | Temporada {month}'
            description = f'Confira os pontos, jogadores e emblemas da temporada {month} da Arena {mode} de AoM Retold. Consulte as regras e o histórico dos rankings mensais.'
            label = f'Temporada {month} · {mode}'
            if queue != 'x1':
                query['modo'] = queue
            if season and season != context.get('current'):
                query['mes'] = season
        if ep == 'hub_rivalry':
            a, b = context.get('a'), context.get('b')
            aname, bname = plain(field(a, 'nickname')), plain(field(b, 'nickname'))
            title = f'{aname} × {bname} | Rivalidade no AoM Retold'
            description = f'Compare os confrontos de {aname} e {bname}: placar da rivalidade, últimas vitórias, maior sequência e histórico de partidas na Arena X1.'
            ids = sorted((values['player_a'], values['player_b']))
            canonical = absolute('hub_rivalry', player_a=ids[0], player_b=ids[1])
            indexed = indexed and bool(field(context.get('rival'), 'history', []))
            label = f'{aname} × {bname}'
        if ep == 'hub_replay':
            replay, event = context.get('replay'), context.get('event')
            title = f'Replay #{field(replay,"id")}: {plain(field(event,"title"))}'
            description = f'Replay de {plain(field(event,"title"))} no AoM Retold. Baixe a partida e consulte os comentários de análise. {plain(field(replay,"description"))}'
            label = f'Replay #{field(replay,"id")}'

        # Real pagination keeps its own address. Tracking parameters never enter canonicals.
        if ep in ('social_profile', 'social_duel_history', 'teams_arena', 'teams_history', 'hub_rivalry', 'hub_replay'):
            page = field(history, 'page', context.get('page', 1))
            if ep == 'hub_replay':
                page = field(context.get('discussion'), 'page', 1)
            if page > 1:
                query['pagina'] = page
                title += f' · Página {page}'
                description = f'Página {page}. ' + description
            category = field(history, 'category', 'todos')
            if category != 'todos':
                query['filtro'] = category
                indexed = False
            for key in ('jogador', 'equipe'):
                number = request.args.get(key, type=int)
                if number and number > 0 and ep in ('social_duel_history', 'teams_history'):
                    query[key] = number
                    indexed = False
        if ep == 'social_profile' and any(request.args.get(k) for k in ('evo_mes', 'evo_modo')):
            indexed = False
        if canonical and query:
            canonical += '?' + urlencode(sorted(query.items()))

        arena_pages = {'x1_page','social_profile','social_duel_history','social_duel','social_duel_invite_share','social_duel_result_share','teams_arena','teams_history','teams_profile','teams_duel','arena_seasons_page','hub_rivalry','hub_replay'}
        if ep in arena_pages and ep != 'x1_page':
            crumbs.append({'name':'Arena','url':absolute('x1_page')})
        if canonical and ep != 'home':
            crumbs.append({'name':plain(label, 100), 'url':canonical})
        title = plain(title or name, 130)
        if name.casefold() not in title.casefold() and ep != 'knowledge_build_page':
            title += ' | ' + name
        description = plain(description or f'Consulte {title} no Chamas Flamejantes.', 175)
        robots = INDEX if indexed else NOINDEX if ep in PUBLIC_PAGES else PRIVATE
        g.seo_robots = robots
        graph = []
        if indexed:
            web_id, org_id = absolute('home')+'#website', absolute('home')+'#community'
            webpage = {'@type':'WebPage','@id':canonical+'#webpage','url':canonical,'name':title,'description':description,'inLanguage':'pt-BR','isPartOf':{'@id':web_id}}
            if ep == 'home':
                graph.extend([
                    {'@type':'WebSite','@id':web_id,'url':absolute('home'),'name':name,'alternateName':'Chamas Flamejantes AoM','inLanguage':'pt-BR','publisher':{'@id':org_id}},
                    {'@type':'Organization','@id':org_id,'name':name,'url':absolute('home'),'logo':origin()+url_for('static',filename='brand/logo-512.png')},
                ])
            if len(crumbs) > 1:
                webpage['breadcrumb'] = {'@id':canonical+'#breadcrumb'}
                graph.append({'@type':'BreadcrumbList','@id':canonical+'#breadcrumb','itemListElement':[{'@type':'ListItem','position':i,'name':c['name'],'item':c['url']} for i,c in enumerate(crumbs,1)]})
            graph.append(webpage)
        return {'title':title,'description':description,'canonical':canonical,'robots':robots,
                'structured_data':{'@context':'https://schema.org','@graph':graph} if graph else None,
                'verification':verification() if ep == 'home' and not context.get('error_code') else ''}

    app.jinja_env.globals['seo_page'] = page_metadata

    @app.after_request
    def search_headers(response):
        ep = request.endpoint or ''
        if response.status_code >= 400:
            response.headers['X-Robots-Tag'] = PRIVATE
        elif ep == 'static' and (request.view_args or {}).get('filename') == 'guia_de_teclas_aom_retold.html':
            response.headers.add('Link', f'<{absolute("hotkeys_guide_page")}>; rel="canonical"')
        elif (request.path.startswith('/api/') or ep == 'health' or
              'attachment' in response.headers.get('Content-Disposition','').lower() or
              (response.mimetype == 'text/html' and ep not in PUBLIC_PAGES)):
            response.headers['X-Robots-Tag'] = PRIVATE
        elif response.mimetype == 'text/html' and 'seo_robots' in g:
            response.headers['X-Robots-Tag'] = g.seo_robots
        return response

    def sitemap_entries():
        db, entries = api['get_db'](), {}
        def add(endpoint, lastmod=None, **values):
            loc = absolute(endpoint, **values)
            entry = {'loc':loc}
            stamp = modified(lastmod)
            if stamp:
                entry['lastmod'] = stamp
            entries[loc] = entry
        for endpoint, _ in STATIC_DISCOVERY:
            add(endpoint)
        add('teams_arena', modo='3v3')
        for queue in ('2v2','3v3'):
            add('arena_seasons_page', modo=queue)
        current = api['arena_seasons'].period()
        for row in db.execute('SELECT season FROM arena_seasons ORDER BY season DESC LIMIT 36'):
            if row['season'] == current:
                continue
            for queue in ('x1','2v2','3v3'):
                values = {'mes':row['season']}
                if queue != 'x1':
                    values['modo'] = queue
                add('arena_seasons_page', **values)
        for row in db.execute('SELECT slug,status,updated_at FROM tournaments WHERE is_public=1 ORDER BY id'):
            for endpoint in ('tournament_page','tournament_participants','tournament_matches'):
                add(endpoint, slug=row['slug'], lastmod=row['updated_at'])
            if row['status'] == 'finalizado':
                add('tournament_result', slug=row['slug'], lastmod=row['updated_at'])
        catalog = api['knowledge_catalog']()
        for gods in catalog.get('gods',{}).values():
            for god in gods:
                add('knowledge_god_page',god_slug=api['knowledge_god_slug'](god))
        for build in catalog.get('builds',[]):
            add('knowledge_build_page',god_slug=api['knowledge_god_slug'](build['god']),build_id=build['id'])
        for row in db.execute("SELECT id FROM players WHERE is_active=1 AND COALESCE(aomstats_profile_id,'')<>'' AND COALESCE(aomstats_url,'')<>'' ORDER BY id"):
            add('social_profile',player_id=row['id'])
        for row in db.execute("SELECT share_token,finished_at FROM social_duels WHERE status='completed' AND winner_id IS NOT NULL AND loser_id IS NOT NULL ORDER BY id"):
            add('social_duel_result_share',share_token=row['share_token'],lastmod=row['finished_at'])
        for row in db.execute("SELECT t.id FROM arena_teams t WHERE t.archived=0 AND t.size=(SELECT COUNT(*) FROM arena_team_members m WHERE m.team_id=t.id AND m.state='accepted') ORDER BY t.id"):
            add('teams_profile',tid=row['id'])
        for row in db.execute("SELECT id,finished_at FROM arena_team_duels WHERE status='completed' AND winner_side IS NOT NULL ORDER BY id"):
            add('teams_duel',did=row['id'],lastmod=row['finished_at'])
        for row in db.execute("""SELECT DISTINCT MIN(d.challenger_id,d.challenged_id) a,MAX(d.challenger_id,d.challenged_id) b
          FROM social_duels d JOIN players a ON a.id=d.challenger_id JOIN players b ON b.id=d.challenged_id
          WHERE d.status='completed' AND a.is_active=1 AND b.is_active=1 ORDER BY 1,2"""):
            add('hub_rivalry',player_a=row['a'],player_b=row['b'])
        for row in db.execute("""SELECT r.id FROM arena_replays r
          LEFT JOIN social_duels x ON r.queue='x1' AND x.id=r.event_id
          LEFT JOIN arena_team_duels t ON r.queue IN ('2v2','3v3') AND t.id=r.event_id
          WHERE r.deleted=0 AND (x.status='completed' OR t.status='completed') ORDER BY r.id"""):
            add('hub_replay',replay_id=row['id'])
        return list(entries.values())

    def xml_response(entries, index=False):
        root = ET.Element('sitemapindex' if index else 'urlset',xmlns=XMLNS)
        for entry in entries:
            node = ET.SubElement(root,'sitemap' if index else 'url')
            for key,value in entry.items():
                ET.SubElement(node,key).text = value
        response = app.response_class(ET.tostring(root,encoding='utf-8',xml_declaration=True),mimetype='application/xml')
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response

    def sitemap():
        entries = sitemap_entries()
        if len(entries) <= SITEMAP_LIMIT:
            return xml_response(entries)
        return xml_response([{'loc':absolute('sitemap_part',page=i+1)} for i in range((len(entries)+SITEMAP_LIMIT-1)//SITEMAP_LIMIT)],index=True)


    @app.get('/sitemaps/<int:page>.xml')
    def sitemap_part(page):
        entries = sitemap_entries()
        start = (page-1)*SITEMAP_LIMIT
        if page < 1 or start >= len(entries):
            abort(404)
        return xml_response(entries[start:start+SITEMAP_LIMIT])

    def robots():
        # Login/account pages are crawlable so Google can read their noindex directive.
        content = '\n'.join(('User-agent: *','Disallow: /api/','Disallow: /auth/',
                             'Disallow: /admin/backup.sqlite','Allow: /',f'Sitemap: {absolute("sitemap_xml")}',''))
        response = app.response_class(content,mimetype='text/plain')
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response


    @app.get('/mapa-do-site')
    def site_directory():
        sections = [{'name':label,'url':url_for(endpoint)} for endpoint,label in STATIC_DISCOVERY if endpoint != 'site_directory']
        sections.append({'name':'Arena de trios','url':url_for('teams_arena',modo='3v3')})
        catalog, groups = api['knowledge_catalog'](), []
        for gods in catalog.get('gods',{}).values():
            for god in gods:
                slug = api['knowledge_god_slug'](god)
                groups.append({'name':god,'url':url_for('knowledge_god_page',god_slug=slug),
                               'builds':[{'name':b['title'],'url':url_for('knowledge_build_page',god_slug=slug,build_id=b['id'])} for b in catalog['builds'] if b['god']==god]})
        return render_template('site_directory.html',sections=sections,god_groups=groups)

    @app.route('/admin/seo',methods=['GET','POST'])
    @api['admin_required']
    def admin_seo():
        if request.method == 'POST':
            api['require_csrf']()
            raw = request.form.get('verification','').strip()
            if len(raw) > 2048:
                abort(400)
            if raw.startswith('<'):
                node = api['BeautifulSoup'](raw,'html.parser').find('meta',attrs={'name':'google-site-verification'})
                raw = str(node.get('content','')).strip() if node else '!invalid'
            if raw and not re.fullmatch(r'[A-Za-z0-9_-]{10,256}',raw):
                flash('Cole o código de verificação ou a meta tag fornecida pelo Google Search Console.','error')
                return redirect(url_for('admin_seo'))
            if os.environ.get('GOOGLE_SITE_VERIFICATION','').strip():
                flash('O código está definido nas variáveis do Railway. Altere GOOGLE_SITE_VERIFICATION para atualizá-lo.','error')
                return redirect(url_for('admin_seo'))
            db = api['get_db']()
            db.execute("INSERT INTO site_meta(key,value) VALUES('google_site_verification',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(raw,))
            db.commit()
            flash('Código de verificação atualizado. Conclua a verificação no Google Search Console.','success')
            return redirect(url_for('admin_seo'))
        return render_template('admin_seo.html',seo_origin=origin(),verification=verification(),
                               verification_from_env=bool(os.environ.get('GOOGLE_SITE_VERIFICATION','').strip()),
                               sitemap_count=len(sitemap_entries()))

    app.extensions['site_seo'] = {'sitemap_entries':sitemap_entries,'sitemap':sitemap,'robots':robots}
