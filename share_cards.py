"""Server-rendered social artwork. Text and scores always come from site records."""
from functools import lru_cache
from pathlib import Path
import io
import math
import re

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
SIZE = (1200, 630)
GOLD = '#f5c778'
WHITE = '#f7f2e8'
MUTED = '#aab1bb'
MODE_STYLES = {
    'ffa': ('FFA', 'CADA JOGADOR POR SI', '#f48b45', 'zeus'),
    'food_wood_gold': ('3 × 3', 'FOOD · WOOD · GOLD', '#e8ba62', 'ra'),
    '1v1_round_robin': ('1 × 1', 'TODOS CONTRA TODOS', '#8cc4ec', 'poseidon'),
    '2v2_elimination': ('2 × 2', 'DUPLAS · ELIMINAÇÃO', '#67d7c3', 'hades'),
    'bo3_1v1': ('1 × 1', 'MELHOR DE 3', '#bd9fe8', 'odin'),
    'bo3_2v2': ('2 × 2', 'MELHOR DE 3', '#80bced', 'poseidon'),
    'bo3_3v3': ('3 × 3', 'MELHOR DE 3', '#f2917d', 'zeus'),
}


def clean(text):
    text = re.sub(r'<color[^>]*>|</color>', '', str(text or ''), flags=re.I)
    return ' '.join(text.split())[:250]


@lru_cache(maxsize=100)
def font(size, serif=False, bold=True):
    filename = 'DejaVuSerif-Bold.ttf' if serif else ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    return ImageFont.truetype(str(ROOT / 'static' / 'fonts' / filename), size)


def fit(draw, text, width, size=32, minimum=18, serif=False):
    text = clean(text)
    while size > minimum and draw.textlength(text, font=font(size, serif)) > width:
        size -= 1
    f = font(size, serif)
    while text and draw.textlength(text, font=f) > width:
        text = text[:-2].rstrip() + '…'
    return text, f


def centered(draw, x, y, text, width, size=30, fill=WHITE, serif=False):
    value, face = fit(draw, text, width, size, serif=serif)
    draw.text((x, y), value, font=face, fill=fill, anchor='mt')


def paragraph(draw, text, box, size=25, lines=2, fill=WHITE, serif=False):
    x, y, width = box
    words = clean(text).split()
    for current_size in range(size, 18, -1):
        face = font(current_size, serif)
        result, line = [], ''
        for word in words:
            candidate = (line + ' ' + word).strip()
            if line and draw.textlength(candidate, font=face) > width:
                result.append(line)
                line = word
            else:
                line = candidate
        if line:
            result.append(line)
        if len(result) <= lines:
            break
    for index, line in enumerate(result[:lines]):
        if index == lines - 1 and len(result) > lines:
            line += '…'
        value, face = fit(draw, line, width, current_size, serif=serif)
        draw.text((x, y + index * (current_size + 13)), value, font=face, fill=fill)


@lru_cache(maxsize=12)
def backdrop(accent, god):
    canvas = Image.new('RGB', SIZE, '#080d13')
    portrait = ROOT / 'static' / 'knowledge' / 'gods' / f'{god}.webp'
    if portrait.exists():
        with Image.open(portrait) as source:
            art = ImageOps.fit(source.convert('RGB'), SIZE, centering=(.5, .28))
        canvas = Image.blend(canvas, art, .13)
    glaze = Image.new('RGBA', SIZE)
    d = ImageDraw.Draw(glaze)
    rgb = tuple(int(accent[i:i+2],16) for i in (1,3,5))
    for radius in range(430, 0, -12):
        d.ellipse((-230-radius, 20-radius, -230+radius, 20+radius), fill=(*rgb, 15))
        d.ellipse((1100-radius, 410-radius, 1100+radius, 410+radius), outline=(*rgb, 12), width=5)
    canvas = Image.alpha_composite(canvas.convert('RGBA'), glaze.filter(ImageFilter.GaussianBlur(42)))
    d = ImageDraw.Draw(canvas)
    d.rectangle((22, 22, 1177, 607), outline='#484138', width=1)
    for x, y, dx, dy in [(22,22,1,1),(1177,22,-1,1),(22,607,1,-1),(1177,607,-1,-1)]:
        d.line([(x,y+dy*27),(x,y),(x+dx*70,y)], fill=accent, width=3)
    logo = ROOT / 'static' / 'brand' / 'logo-512.png'
    with Image.open(logo) as src:
        mark = src.convert('RGBA').resize((38,38), Image.Resampling.LANCZOS)
    canvas.alpha_composite(mark,(53,45))
    d.text((104,50), 'CHAMAS FLAMEJANTES', font=font(22), fill=WHITE)
    d.text((1147,55), 'AGE OF MYTHOLOGY: RETOLD', font=font(14), fill=MUTED, anchor='rt')
    d.line((53,96,1147,96), fill='#41392f', width=1)
    d.text((54,573), 'chamasflamejantes.com.br', font=font(17), fill=MUTED)
    return canvas


def player_medallion(canvas, player, xy, loader, color, victory=False, broken=False):
    cx, cy = xy
    size = 206
    avatar, mask = loader(player, size)
    avatar = avatar.convert('RGBA')
    if broken:
        avatar = ImageEnhance.Color(avatar).enhance(.35)
        avatar = ImageEnhance.Brightness(avatar).enhance(.8)
        fracture = Image.new('RGBA', avatar.size)
        d = ImageDraw.Draw(fracture)
        paths = [[(122,0),(107,45),(127,79),(92,118),(99,161),(68,206)],
                 [(0,120),(46,103),(92,118),(154,145),(206,125)],
                 [(127,79),(157,49),(196,56)]]
        for points in paths:
            d.line(points, fill='#070b10', width=8, joint='curve')
            d.line([(x+3,y) for x,y in points], fill='#ddada096', width=2, joint='curve')
        avatar = Image.alpha_composite(avatar,fracture)
    canvas.paste(avatar, (cx-size//2, cy-size//2), mask)
    draw = ImageDraw.Draw(canvas)
    if broken:
        for start,end in [(6,82),(90,200),(210,294),(305,356)]:
            draw.arc((cx-111,cy-111,cx+111,cy+111),start,end,fill=color,width=5)
        draw.polygon([(cx+115,cy+2),(cx+128,cy-11),(cx+125,cy+18)],fill='#89726c')
    else:
        draw.ellipse((cx-111,cy-111,cx+111,cy+111),outline=color,width=5)
        draw.ellipse((cx-118,cy-118,cx+118,cy+118),outline='#886b3c' if victory else '#70462e',width=1)
    if victory:
        for side in (-1,1):
            for i in range(5):
                angle = math.radians(22 + i*12)
                x = cx + side*math.cos(angle)*130
                y = cy + math.sin(angle)*112
                draw.polygon([(x,y-11),(x+side*12,y-19),(x+side*8,y+2),(x,y+8)],fill=color)
        draw.polygon([(cx-33,cy-115),(cx-43,cy-146),(cx-17,cy-134),(cx,cy-158),
                      (cx+17,cy-134),(cx+43,cy-146),(cx+33,cy-115)],fill=color)
        draw.line((cx-30,cy-111,cx+30,cy-111),fill=color,width=4)


def render_arena_card(duel, avatar_loader, output_format='JPEG'):
    completed = duel['status'] == 'completed'
    refused = duel['status'] == 'refused'
    canvas = backdrop(GOLD if completed else '#ec864b', 'zeus').copy()
    draw = ImageDraw.Draw(canvas)
    heading = 'VITÓRIA' if completed else ('DESAFIO RECUSADO' if refused else 'DUELO NA ARENA')
    centered(draw,600,114,heading,1080,70 if completed else 51,GOLD if completed else WHITE,True)
    first = duel['winner'] if completed else duel['challenger']
    second = duel['loser'] if completed else duel['challenged']
    for rect in [(55,206,465,543),(735,206,1145,543)]:
        draw.rectangle(rect,fill='#0e141c',outline='#3b3937',width=1)
    draw.rectangle((55,206,465,209),fill=GOLD if completed else '#ec864b')
    draw.rectangle((735,206,1145,209),fill='#99776d' if completed else '#ec864b')
    player_medallion(canvas,first,(260,358),avatar_loader,GOLD if completed else '#ed945f',victory=completed)
    player_medallion(canvas,second,(940,358),avatar_loader,'#9f8c84' if completed else '#ed945f',broken=completed)
    draw = ImageDraw.Draw(canvas)
    centered(draw,260,486,first['nickname'],380,30,WHITE)
    centered(draw,940,486,second['nickname'],380,30,'#c4c5c8' if completed else WHITE)
    centered(draw,260,520,'VENCEDOR' if completed else 'DESAFIANTE',350,15,GOLD)
    centered(draw,940,520,'DERROTADO' if completed else 'DESAFIADO',350,15,MUTED)
    centered(draw,600,289,'VENCEU' if completed else 'VS',238,43 if completed else 68,GOLD,True)
    label = ('RESULTADO CONFIRMADO' if completed else 'FUGIU DA BATALHA' if refused else
             'AGUARDANDO RESPOSTA' if duel['status']=='pending' else 'DESAFIO ACEITO')
    centered(draw,600,364,label,248,16,MUTED)
    if duel.get('match_id'):
        centered(draw,600,401,'#'+duel['match_id'],230,26,WHITE)
    if duel.get('match_map'):
        centered(draw,600,445,duel['match_map'],230,19,MUTED)
    if duel.get('match_duration'):
        centered(draw,600,476,duel['match_duration'],230,17,MUTED)
    foot = 'VERIFICADO PELO AOMSTATS' if completed else 'ACOMPANHE O DESAFIO NO SITE'
    draw.text((1147,575),foot,font=font(14),fill=GOLD,anchor='rt')
    return encoded(canvas,output_format)


def render_team_card(duel, avatar_loader):
    completed = duel['status']=='completed'
    canvas = backdrop(GOLD if completed else '#65cabb','poseidon' if duel['size']==2 else 'zeus').copy()
    draw=ImageDraw.Draw(canvas)
    centered(draw,600,114,('VITÓRIA EM EQUIPE' if completed else f"ARENA {duel['size']} × {duel['size']}"),1080,52,GOLD,True)
    left=duel['winner_side'] if completed else 'a'
    right='b' if left=='a' else 'a'
    for index,side in enumerate((left,right)):
        cx=302 if index==0 else 898
        color=GOLD if completed and index==0 else '#829197' if completed else '#65cabb'
        draw.rounded_rectangle((cx-244,202,cx+244,538),12,fill='#0e141c',outline=color,width=2)
        centered(draw,cx,220,duel['name_'+side],460,32,WHITE)
        members=duel[side]; count=len(members)
        for i,m in enumerate(members):
            x=round(cx+(i-(count-1)/2)*148); y=345
            source,mask=avatar_loader(m['profile'],112)
            if completed and index==1:
                source=ImageEnhance.Color(source.convert('RGB')).enhance(.22)
                crack=ImageDraw.Draw(source)
                crack.line([(67,0),(53,28),(72,50),(49,78),(56,112)],fill='#10141b',width=5)
            canvas.paste(source,(x-56,y-56),mask)
            draw=ImageDraw.Draw(canvas)
            draw.ellipse((x-61,y-61,x+61,y+61),outline=color,width=3)
            if completed and index==0:
                draw.polygon([(x-18,y-67),(x-25,y-89),(x-8,y-80),(x,y-98),(x+8,y-80),(x+25,y-89),(x+18,y-67)],fill=GOLD)
            centered(draw,x,424,m['profile']['nickname'],140,19,WHITE)
        centered(draw,cx,494,('VENCEDORES' if index==0 else 'DERROTADOS') if completed else ('DESAFIANTES' if index==0 else 'DESAFIADOS'),460,17,color)
    centered(draw,600,341,'VENCEU' if completed else 'VS',90,23,GOLD,True)
    detail=f"{duel['size']}×{duel['size']}" + (f" · PARTIDA #{duel['match_id']}" if duel['match_id'] else ' · DESAFIO DA COMUNIDADE')
    draw.text((1147,575),detail,font=font(16),fill=GOLD,anchor='rt')
    return encoded(canvas,'JPEG')


def tournament_style(tournament):
    return MODE_STYLES.get(tournament['mode_key'], (
        f"{tournament['team_size']} × {tournament['team_size']}",
        'MELHOR DE 3' if tournament['best_of']==3 else 'TORNEIO DA COMUNIDADE', '#ed945f', 'zeus'))


def render_tournament_card(tournament, output_format='JPEG'):
    mode, caption, accent, god = tournament_style(tournament)
    canvas = backdrop(accent,god).copy()
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((55,121,430,157),radius=3,fill=accent)
    draw.text((72,128),tournament['share_status'],font=font(17),fill='#10141b')
    paragraph(draw,tournament['name'],(55,188,640),size=47,lines=2,serif=True)
    paragraph(draw,tournament.get('description') or caption,(58,327,608),size=24,lines=2,fill=MUTED)
    facts = [('PREMIAÇÃO', tournament['share_prize']),
             ('DATA', tournament.get('event_date') or 'A definir'),
             ('INSCRITOS', f"{tournament['filled']}/{tournament['max_entries']} " + ('equipes' if tournament['team_size']>1 else 'jogadores'))]
    for i,(label,value) in enumerate(facts):
        x=55+i*214
        draw.rectangle((x,439,x+197,535),fill='#111821',outline='#393a3a')
        draw.text((x+14,456),label,font=font(13),fill=MUTED)
        value,face=fit(draw,value,170,23)
        draw.text((x+14,487),value,font=face,fill=accent if i==0 else WHITE)
    portrait=ROOT/'static'/'knowledge'/'gods'/f'{god}.webp'
    with Image.open(portrait) as src:
        art=ImageOps.fit(src.convert('RGB'),(420,431),centering=(.5,.22))
    art=Image.blend(Image.new('RGB',art.size,'#080f18'),art,.6).convert('RGBA')
    canvas.alpha_composite(art,(725,114))
    shade=Image.new('RGBA',(420,431))
    sd=ImageDraw.Draw(shade)
    for y in range(431):
        sd.line((0,y,419,y),fill=(5,10,16,int(195*max(0,(y-110)/320))))
    canvas.alpha_composite(shade,(725,114))
    draw=ImageDraw.Draw(canvas)
    draw.rectangle((725,114,1145,545),outline=accent,width=2)
    draw.rectangle((725,114,1145,119),fill=accent)
    if tournament['best_of']==3:
        centered(draw,935,156,'MD3',360,78,accent,True)
        centered(draw,935,253,mode,350,65,WHITE,True)
        centered(draw,935,347,'PRIMEIRO A 2 VITÓRIAS',360,19,WHITE)
        for i in range(3):
            x=883+i*44
            draw.polygon([(x,402),(x+12,414),(x,426),(x-12,414)],fill=accent if i<2 else '#27313c',outline=accent)
    elif tournament['mode_key']=='food_wood_gold':
        centered(draw,935,170,'3 × 3',360,83,WHITE,True)
        for i,(word,tone) in enumerate([('FOOD','#ef8b70'),('WOOD','#a9c990'),('GOLD','#f0c971')]):
            x=792+i*140
            draw.ellipse((x-26,316,x+26,368),outline=tone,width=3)
            centered(draw,x,330,word[0],44,26,tone)
            centered(draw,x,388,word,125,18,tone)
    else:
        centered(draw,935,216,mode,370,91,WHITE,True)
        centered(draw,935,351,'ARENA LIVRE' if tournament['mode_key']=='ffa' else 'TORNEIO DA COMUNIDADE',370,19,accent)
        count=6 if tournament['mode_key']=='ffa' else tournament['team_size']*2
        for i in range(count):
            x=935+(i-(count-1)/2)*35
            draw.polygon([(x,404),(x+8,412),(x,420),(x-8,412)],fill=accent)
    centered(draw,935,475,caption,376,20,accent)
    draw.text((1147,575),'ABRA O LINK E VEJA O TORNEIO',font=font(14),fill=accent,anchor='rt')
    return encoded(canvas,output_format)


def encoded(canvas, output_format='JPEG'):
    output=io.BytesIO()
    if output_format=='PNG':
        canvas.convert('RGB').save(output,'PNG',optimize=True)
    else:
        canvas.convert('RGB').save(output,'JPEG',quality=87,optimize=True,progressive=True)
    output.seek(0)
    return output
