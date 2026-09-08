# 🔥 CHAMAS FLAMEJANTES V21 — ARENA UNIFICADA

Build configurado com Railpack, o construtor atual do Railway.

Menu superior sem destaque permanente; todas as abas recebem destaque ao passar o mouse.

A navegação principal usa abas de altura uniforme, textos alinhados e organização responsiva. A aba Programas não possui mais o ícone de disquete.

As abas ocupam toda a largura disponível da moldura, sem deixar uma faixa vazia no lado esquerdo.

## Google e outros buscadores

- Sitemap automático disponível em `https://chamasflamejantes.com.br/sitemap.xml`.
- `robots.txt` disponível em `https://chamasflamejantes.com.br/robots.txt`, apontando para o sitemap.
- O sitemap inclui páginas públicas, torneios públicos, os 23 deuses, todas as build orders, o Guia de Counters e o Guia de Teclas.
- Login, configuração e painel administrativo não são enviados no sitemap.
- Novos torneios marcados como públicos entram automaticamente no sitemap.

Depois do deploy, abra o Google Search Console, verifique o domínio e envie `sitemap.xml` na opção **Sitemaps**.

Base visual e cadastro de jogadores preservados do projeto V7.5, com recursos V11 integrados.

## Railway

1. Envie todo o projeto ao GitHub e conecte o repositório ao Railway.
2. Crie um volume persistente montado em `/app/data`.
3. Configure a variável `FFA_SECRET_KEY` com uma chave longa e secreta.
4. Opcional: configure `DATABASE_PATH=/app/data/chamas_flamejantes.sqlite`.
5. Opcional: configure `MAX_UPLOAD_MB=250` para ajustar o limite dos arquivos enviados pelo painel.
6. O Railway inicia pelo `railway.json` e verifica `/health`.

### Login Google dos jogadores

Crie um cliente OAuth 2.0 do tipo **Aplicativo da Web** no Google Cloud e configure no Railway:

```env
PUBLIC_BASE_URL=https://chamasflamejantes.com.br
GOOGLE_CLIENT_ID=SEU_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=SEU_CLIENT_SECRET
```

No cliente OAuth do Google, adicione exatamente este URI de redirecionamento autorizado:

```text
https://chamasflamejantes.com.br/auth/google/callback
```

Se quiser usar outro endereço no callback, configure também `GOOGLE_REDIRECT_URI` no Railway e cadastre o mesmo endereço no Google Cloud. O endpoint `/health` mostra `google_oauth: configured` quando as duas credenciais foram reconhecidas.

O SQLite é criado automaticamente na primeira inicialização.

## Administrador

O login administrativo não aparece no menu público. Digite `/admin/login` no final do endereço do site. A atualização preserva o administrador e a senha que já estão no banco.

Em uma instalação totalmente nova, abra `/setup` uma única vez e crie o primeiro administrador. A versão não publica nem recria uma senha administrativa padrão.

## Recursos

- Cadastro original V7.5 com busca AoMStats e foto Steam automática.
- Inscrição individual e de equipes, incluindo FOOD/WOOD/GOLD.
- Torneios FFA, 1x1, 2x2, 3x3 e Melhor de 3.
- Classificação, confrontos, vencedores e histórico.
- Elo da Comunidade, frases e patrocinadores.
- Mini rede social com login Google, perfil público e frase pessoal.
- Ao vincular o AoMStats, o jogador entra automaticamente no Elo da Comunidade e na Arena X1; sem AoMStats ele não aparece nessas áreas.
- Cards compactos de jogadores e ranking da Arena posicionado ao lado da lista.
- Histórico de duelos em página própria, acessível por botão na Arena e nos perfis.
- Janela flutuante de notificações em formato de conversa, com aceite e recusa do desafio no próprio painel.
- Tela pública do perfil limpa, com a edição de AoMStats, frase e foto aberta somente pelo botão “Alterar meus dados”.
- Códigos de nick como `<color1,0.2,0.6>` são ocultados e a cor correspondente é aplicada ao nome.
- Inscrição individual em torneio feita em um clique com o AoMStats já vinculado à conta Google.
- Exclusão administrativa desativa a conta, preserva os resultados antigos e permite que o jogador se cadastre novamente.
- Perfil preenchido automaticamente pelo AoMStats, foto Steam por padrão e upload opcional pelo PC.
- Cards de perfil no estilo da Área de Conhecimento e janela flutuante ao clicar nas fotos.
- Desafio X1 criado somente dentro do perfil do jogador-alvo.
- Notificações internas, caixa de desafios em formato de mensagem e resposta Aceitar/Recusar.
- Recusas registradas no histórico como “Fugiu da batalha”.
- ID da partida enviado somente pelos dois participantes depois do desafio ser aceito.
- Consulta de `https://aomstats.io/match/ID`, validação dos dois perfis e registro automático do vencedor.
- Estado “Partida em andamento” enquanto o AoMStats ainda não encontrar ou finalizar o ID.
- Ranking da Arena X1 calculado apenas com resultados confirmados.
- Cards compartilháveis de perfis e resultados, com metadados Open Graph e fotos dos jogadores.
- Convites de desafio possuem link público com token e imagem Open Graph própria para aparecer no WhatsApp e em outras redes.
- Atalhos de compartilhamento para WhatsApp, Telegram, Facebook, X e menu nativo do aparelho.
- Upload e download de mapas ZIP, RAR e 7Z.
- Programas oficiais com imagem, descrição, contador de downloads e publicação por arquivo RAR ou URL externa.
- Atalho destacado para Programas Oficiais na navegação e na página inicial.
- Rodapé com redes sociais oficiais e perfil do criador integrado ao AoMStats/Steam.
- Links oficiais para WhatsApp, Discord e Telegram.
- Busca de mapas por nome, criador ou categoria, com listas separadas e imagens completas.
- Cards de mapas no mesmo acabamento visual da Área de Conhecimento, mantendo a busca existente.
- Pedidos de mapas enviados pelo público com identificação via perfil AoMStats.
- Área pública de feedback, com mensagens privadas para o painel do administrador.
- Administração de feedbacks e pedidos de mapas com status e exclusão.
- Links oficiais com logos de WhatsApp, Discord e YouTube.
- Área de Conhecimento com três páginas próprias: Guia de Teclas, Guia de Counters e Biblioteca de Build Orders.
- Guia interativo de teclas do AoM Retold com consulta, simulação e personalização de XML.
- O Guia de Teclas abre dentro da estrutura do site e mantém o menu principal sempre visível.
- O HTML direto do Guia de Teclas também possui um menu de segurança; dentro do site, apenas o menu principal é exibido.
- O último colocado agora recebe o título “Menor Elo” na página inicial, na comunidade e no painel.
- Biblioteca com 113 build orders de 23 deuses atuais.
- Guia interativo de counters acessível por um card acima da pesquisa da Área de Conhecimento.
- Catálogo completo com 251 unidades de 7 panteões, separado em unidades humanas, heróis, míticas, cerco, navais e Titãs.
- Seleção do panteão inimigo, counters diretos por classe e multiplicador, custos, pontos de vida e ranking de caçadores de Titãs.
- O painel “Quem mata Titãs mais rápido?” fica abaixo do elenco para não atrapalhar a pesquisa de unidades.
- Cards de unidades no mesmo acabamento visual da Área de Conhecimento, com ícones completos e pesquisa por nome, categoria ou deus.
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

A atualização cria ou preserva automaticamente as tabelas `social_accounts`, `social_duels` e `social_notifications`, além dos campos de cor e ativação do perfil, sem apagar inscrições ou resultados existentes. Os duelos antigos são copiados uma única vez para o novo histórico. As tabelas `feedback_entries`, `map_requests`, `official_programs` e seus arquivos permanecem preservados.

A Área de Conhecimento e o Guia de Counters são estáticos e não alteram cadastros. Os catálogos ficam em `knowledge_data/build_orders.json` e `static/counters/units.json`, fora do volume `/app/data`, para permanecerem disponíveis no Railway.

## Execução local

```bash
pip install -r requirements.txt
python app.py
```
