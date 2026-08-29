# 🔥 CHAMAS FLAMEJANTES V14.0 — RAILWAY

Build configurado com Railpack, o construtor atual do Railway.

Menu superior sem destaque permanente; todas as abas recebem destaque ao passar o mouse.

Base visual e cadastro de jogadores preservados do projeto V7.5, com recursos V11 integrados.

## Railway

1. Envie todo o projeto ao GitHub e conecte o repositório ao Railway.
2. Crie um volume persistente montado em `/app/data`.
3. Configure a variável `FFA_SECRET_KEY` com uma chave longa e secreta.
4. Opcional: configure `DATABASE_PATH=/app/data/chamas_flamejantes.sqlite`.
5. Opcional: configure `MAX_UPLOAD_MB=250` para ajustar o limite dos arquivos enviados pelo painel.
6. O Railway inicia pelo `railway.json` e verifica `/health`.

O SQLite é criado automaticamente na primeira inicialização.

## Administrador

O login não aparece no menu público. Digite `/login` no final do endereço do site.

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
- Programas oficiais com imagem, descrição, contador de downloads e publicação por arquivo RAR ou URL externa.
- Atalho destacado para Programas Oficiais na navegação e na página inicial.
- Rodapé com redes sociais oficiais e perfil do criador integrado ao AoMStats/Steam.
- Links oficiais para WhatsApp, Discord e Telegram.
- Busca de mapas por nome, criador ou categoria, com listas separadas e imagens completas.
- Links oficiais com logos de WhatsApp, Discord e YouTube.
- Área de Conhecimento com 113 build orders de 23 deuses atuais.
- Pesquisa e filtros por panteão, deus e tipo de estratégia.
- Rotas essenciais de economia, rush e economia de água para cada deus.
- Passo a passo em português por idade, com 🍖 comida, 🪵 madeira, 🪙 ouro, ✨ favor, 👨‍🌾 aldeões e 🎣 pesca.
- Retratos do Age of Mythology: Retold obtidos separadamente pelo AoMStats; nenhuma imagem do site de build orders foi reutilizada.

## Atualização sem perder dados

Mantenha o volume montado em `/app/data` e a variável:

`DATABASE_PATH=/app/data/chamas_flamejantes.sqlite`

Antes do primeiro deploy desta atualização, abra o Console do serviço atual e copie uploads antigos para o volume:

```bash
mkdir -p /app/data/uploads && cp -a /app/static/uploads/. /app/data/uploads/ 2>/dev/null || true
```

Depois faça o novo deploy. Banco e uploads passarão a permanecer no mesmo volume.

A atualização cria automaticamente apenas a nova tabela `official_programs`, sem apagar ou modificar os registros existentes. Arquivos e imagens dos programas ficam em `/app/data/uploads/programs`.

A Área de Conhecimento continua estática e não altera cadastros. O catálogo fica em `knowledge_data/build_orders.json`, fora do volume `/app/data`, para permanecer disponível no Railway.

## Execução local

```bash
pip install -r requirements.txt
python app.py
```
