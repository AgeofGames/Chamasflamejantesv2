# 🔥 CHAMAS FLAMEJANTES V11 CLEAN

Plataforma Flask + SQLite criada do zero para Railway.

## Deploy no Railway

1. Envie este projeto ao GitHub ou faça upload no Railway.
2. Crie um serviço e adicione um volume persistente montado em `/app/database`.
3. Configure `SECRET_KEY` com uma chave segura.
4. O Railway usará automaticamente o `Procfile`/`railway.json`.
5. Verifique `/health` após o deploy.

Banco novo: `database/chamas_flamejantes.sqlite` (criado automaticamente).

Admin inicial: `yukinochannyan` / `yukinochannyan60`. Altere após entrar.

## Local

```bash
python -m venv .venv
pip install -r requirements.txt
python app.py
```

Abra `http://localhost:5000`.
