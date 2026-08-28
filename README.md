# 🔥 CHAMAS FLAMEJANTES V12.1 — SOCIAL TRIAL + STEAM

Base visual V11.1/V7.5 com mini rede social da comunidade Age of Mythology: Retold.

## Railway

1. Publique os arquivos no mesmo serviço Railway.
2. Mantenha o volume persistente montado em `/app/data`.
3. Mantenha `DATABASE_PATH=/app/data/chamas_flamejantes.sqlite`.
4. Configure uma `FFA_SECRET_KEY` longa e secreta.
5. O Railway inicia pelo `railway.json` e verifica a rota `/health`.

O banco é atualizado de forma aditiva. Jogadores, mapas, torneios e uploads existentes não são removidos.

## Confirmação de e-mail no Railway Trial

Esta versão usa a API HTTPS do Brevo. Não usa SMTP por padrão.

1. Crie uma conta no Brevo.
2. Cadastre e confirme um remetente no painel do Brevo.
3. Crie uma chave em `SMTP & API` → `API Keys`.
4. Adicione no Railway:

```env
EMAIL_PROVIDER=brevo
BREVO_API_KEY=xkeysib-SUA-CHAVE
BREVO_SENDER_EMAIL=seu-email-confirmado@exemplo.com
BREVO_SENDER_NAME=Chamas Flamejantes
PUBLIC_BASE_URL=https://web-production-c5fb8.up.railway.app
```

As variáveis antigas `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` e `SMTP_TLS` podem ser removidas no Railway.

## Rede social

- Cadastro com e-mail e senha criptografada.
- Confirmação por e-mail usando API HTTPS.
- Steam OpenID para confirmar a identidade do jogador.
- AoMStats aceito somente quando pertence à Steam autenticada.
- Foto oficial Steam/AoMStats.
- Perfis públicos completos com descrição, redes, Elo, estatísticas normais e X1.
- Presença online com atualização automática.
- Mensagens recebidas e enviadas com exclusão individual.
- Notificações e contador de itens não lidos.
- Desafios X1 com aceite do jogador e aprovação do administrador.
- Convites para acompanhar duelos.
- Painel público mostrando quem desafia quem.
- Card PNG do vencedor para WhatsApp e Discord.

## Endereços

- Cadastro de jogador: `/cadastro`
- Login de jogador: `/login`
- Comunidade: `/comunidade/painel`
- Administrador oculto: `/admin/login`

Administrador inicial:

- Usuário: `yukinochannyan`
- Senha: `yukinochannyan60`

Altere a senha administrativa depois do primeiro acesso.

## Atualização sem perder dados

Não apague o volume. Antes do primeiro deploy que usa uploads persistentes, execute uma vez no Console:

```bash
mkdir -p /app/data/uploads && cp -a /app/static/uploads/. /app/data/uploads/ 2>/dev/null || true
```

## Execução local

```bash
pip install -r requirements.txt
python app.py
```
