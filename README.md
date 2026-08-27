# 🔥 CHAMAS FLAMEJANTES V12 — SOCIAL + STEAM

Base visual e cadastro de jogadores preservados do projeto V7.5, agora com os recursos sociais V12 integrados.

## Railway

1. Envie todo o projeto ao GitHub e conecte o repositório ao Railway.
2. Crie um volume persistente montado em `/app/data`.
3. Configure a variável `FFA_SECRET_KEY` com uma chave longa e secreta.
4. Opcional: configure `DATABASE_PATH=/app/data/chamas_flamejantes.sqlite`.
5. O Railway inicia pelo `railway.json` e verifica `/health`.

O SQLite é criado automaticamente na primeira inicialização.

## Administrador

O login administrativo não aparece no menu público. Digite `/admin/login` no final do endereço do site.

O endereço `/login` agora pertence às contas dos jogadores.

- Usuário inicial: `yukinochannyan`
- Senha inicial: `yukinochannyan60`

Altere a senha no painel após o primeiro acesso.

## Recursos

- Cadastro original V7.5 com busca AoMStats e foto Steam automática.
- Inscrição individual e de equipes, incluindo FOOD/WOOD/GOLD.
- Torneios FFA, 1x1, 2x2, 3x3 e Melhor de 3.
- Classificação, confrontos, vencedores e histórico.
- Elo da Comunidade, frases e patrocinadores.
- Arena X1 com aprovação e ranking público.
- Upload e download de mapas ZIP, RAR e 7Z.
- Links oficiais para WhatsApp, Discord e Telegram.
- Busca de mapas por nome, criador ou categoria, com listas separadas e imagens completas.
- Links oficiais com logos de WhatsApp, Discord e YouTube.
- Contas de membros com e-mail confirmado e senha criptografada.
- Vinculação segura pela autenticação oficial Steam OpenID.
- Validação de propriedade entre Steam e perfil AoMStats.
- Presença on-line, perfil social, mensagens privadas e notificações.
- Desafios X1 com aceite do jogador e aprovação do administrador.
- Convites para acompanhar duelos e card PNG compartilhável do vencedor.

## E-mail de confirmação no Railway

Adicione estas variáveis no serviço:

- `PUBLIC_BASE_URL=https://SEU-DOMINIO.com.br/`
- `SMTP_HOST` — servidor SMTP do seu provedor de e-mail
- `SMTP_PORT=587`
- `SMTP_USER` — usuário/login SMTP
- `SMTP_PASSWORD` — senha SMTP
- `SMTP_FROM` — endereço que enviará as confirmações
- `SMTP_TLS=1`

Se seu provedor exigir SSL direto, use `SMTP_PORT=465`, `SMTP_SSL=1` e `SMTP_TLS=0`.

## Atualização sem perder dados

Mantenha o volume montado em `/app/data` e a variável:

`DATABASE_PATH=/app/data/chamas_flamejantes.sqlite`

Antes do primeiro deploy desta atualização, abra o Console do serviço atual e copie uploads antigos para o volume:

```bash
mkdir -p /app/data/uploads && cp -a /app/static/uploads/. /app/data/uploads/ 2>/dev/null || true
```

Depois faça o novo deploy. Banco e uploads passarão a permanecer no mesmo volume.

## Execução local

```bash
pip install -r requirements.txt
python app.py
```
