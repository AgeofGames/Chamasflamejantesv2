# 🔥 CHAMAS FLAMEJANTES V11 — VISUAL V7.5

Base visual e cadastro de jogadores preservados do projeto V7.5, com recursos V11 integrados.

## Railway

1. Envie todo o projeto ao GitHub e conecte o repositório ao Railway.
2. Crie um volume persistente montado em `/app/data`.
3. Configure a variável `FFA_SECRET_KEY` com uma chave longa e secreta.
4. Opcional: configure `DATABASE_PATH=/app/data/chamas_flamejantes.sqlite`.
5. O Railway inicia pelo `railway.json` e verifica `/health`.

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
- Links oficiais para WhatsApp, Discord e Telegram.

## Execução local

```bash
pip install -r requirements.txt
python app.py
```
