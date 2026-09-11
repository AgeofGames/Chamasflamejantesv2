# 🔥 CHAMAS FLAMEJANTES V23 — ARENA PÚBLICA E CARDS

## Novidades da V23

- Ao abrir um perfil, a janela flutuante já mostra partidas disputadas, vitórias, derrotas, fugas e os adversários. A página completa também exibe o histórico.
- Filtros **Todos**, **Partidas**, **Vitórias**, **Derrotas**, **Fugas** e **Ativos**, com paginação para consultar os registros antigos.
- Fugas contam apenas os desafios que a própria pessoa recusou. O histórico informa de quem ela fugiu. Desafios cancelados ficam ocultos e não contam como fuga.
- A Arena mostra os desafios ativos da comunidade para todos. Visitantes podem abrir o confronto e ver o ID informado, mesmo antes da confirmação do resultado. Somente os participantes autorizados podem responder ou informar a partida.
- Card de vitória com avatar colorido do vencedor, coroa e moldura dourada; o derrotado aparece com moldura e efeito de rachaduras. Nomes, resultado, mapa, duração e ID vêm do registro do duelo.
- Botões para compartilhar o link no WhatsApp, Facebook, X, Telegram e no menu nativo do aparelho. Também é possível enviar a imagem nos aparelhos compatíveis ou **Baixar card** e anexar em qualquer rede.
- Torneios públicos abertos ou em andamento ganham **Compartilhar torneio** na listagem e na página do evento. Existem artes específicas para FFA, Food/Wood/Gold, 1×1 todos contra todos, 2×2 eliminação e MD3 1×1, 2×2 e 3×3.
- Imagens JPEG públicas em 1200 × 630, metadados completos no HTML inicial, nomes de fonte incluídos no pacote e cache limitado em memória. Os links de imagem mudam de versão quando o conteúdo muda.

**Como atualizar:** envie os arquivos deste pacote ao GitHub, incluindo `share_cards.py`, `static/fonts`, os novos templates, CSS e JavaScript. Preserve o banco, os uploads, o volume e as variáveis existentes do Railway. Após a implantação ativa, `/health` deve informar `23-arena-publica-cards`.

**Validação:** 40 testes Python e 9 testes JavaScript passaram. Foram conferidos permissões, visibilidade pública, filtros e paginação, contagem de fugas, cancelamento, metadados, imagens nas sete modalidades, download e recuperação de falhas no compartilhamento. As imagens renderizadas também foram inspecionadas visualmente. Detalhes em `ARENA_PUBLICA_V23.md`.

O WhatsApp controla a geração e o cache de suas prévias. Compartilhe pelos novos botões em uma mensagem nova; o envio do arquivo de imagem também está disponível. Este pacote inclui todas as correções anteriores de AoMStats, perfis, navegação, favicon e capa do site.

## Atualização da V22.3

- Logo da chama em PNG e ICO, declarado no cabeçalho de todas as páginas. Endereços estáveis `/favicon.png`, `/favicon.ico` e `/apple-touch-icon.png`.
- Capa disponível também em `/capa-chamas-flamejantes.jpg`, sem login, redirecionamento ou consulta ao banco.
- Novo link `https://chamasflamejantes.com.br/compartilhar`: abre a página inicial completa e possui seu próprio endereço Open Graph, para testar uma prévia nova. A URL canônica para o Google continua sendo a raiz do site.
- Botão **Compartilhar site** no rodapé usa esse novo link. No celular, abre o compartilhamento do aparelho quando disponível; nos demais casos, copia o link.
- Metadados de imagem presentes no HTML inicial. Os cards específicos dos perfis e desafios continuam funcionando.

**Como atualizar:** substitua os arquivos do repositório com este pacote, incluindo as pastas `static/brand` e `static/share`. Preserve o volume e as variáveis do Railway. Espere a implantação ficar ativa; `/health` deve informar `22.3-whatsapp-favicon`.

**WhatsApp:** depois da atualização, cole `https://chamasflamejantes.com.br/compartilhar` em uma mensagem nova e aguarde a prévia antes de enviar. Mensagens antigas e prévias já guardadas pelo aplicativo não são alteradas por este pacote. A capa e os metadados da versão anterior já estavam acessíveis na verificação pública; a descrição antiga na captura indica cache, mas o acesso do robô do WhatsApp não foi observado diretamente.

**Google:** no Search Console, inspecione `https://chamasflamejantes.com.br/` e clique em **Solicitar indexação**. O Google precisa rastrear novamente a página e o ícone; isso pode levar dias ou semanas e a exibição não é garantida. [Orientações oficiais sobre favicons](https://developers.google.com/search/docs/appearance/favicon-in-search).

**Validação:** 32 testes Python e 3 testes JavaScript passaram. Os testes verificam o HTML sem execução de JavaScript, a capa e os ícones com GET/HEAD, MIME e dimensões corretos, cache público, ausência de autenticação, a rota de compartilhamento e os fluxos anteriores. Detalhes em `PREVIAS_V22_3.md`.

Todas as correções das versões anteriores estão incluídas.

## Correção da V22.2

- Confirmação de duelos pelo ID exato tanto na página da partida quanto no histórico recente Customs/Quickplay dos dois jogadores.
- Leitura dos IDs dos perfis e dos marcadores explícitos de vitória e derrota, sem inferir resultado pelo nome. Partidas com participantes extras ou dessincronização não são registradas como X1.
- Consultas com limite de tempo e tamanho de resposta; nenhum ciclo automático fica buscando a partida indefinidamente.
- O formulário mostra a resposta sem recarregar a página quando não há resultado. Falhas e tempo esgotado encerram o indicador e liberam os botões.
- Botão **Corrigir o ID da partida** enquanto o resultado não estiver confirmado.
- Estado **Resultado não confirmado**, com informação da última consulta. Barra de leitura removida das páginas de duelo.
- Proteção para não vincular o resultado de um ID a outro caso os dois jogadores alterem a partida ao mesmo tempo.

**Como atualizar:** substitua os arquivos do repositório com este pacote, mantendo o volume e as variáveis do Railway. Depois que `/health` mostrar `22.2-partidas-customs`, abra o duelo já existente e clique em **Verificar novamente**. O ID salvo continua disponível.

**Validação:** 30 testes Python e 3 testes JavaScript passaram. O caso 43115933 (Mirage, 6:08) foi reproduzido com o HTML público observado no AoMStats. Detalhes e limites em `CORRECAO_CUSTOMS_V22_2.md`.

As animações, a capa de compartilhamento e as demais melhorias das versões anteriores estão incluídas.

## Novidade da V22.1

O link principal agora inclui uma capa própria com Zeus, Rá, o nome Chamas Flamejantes e destaque para as 113 build orders. As páginas que usam a prévia padrão também recebem a capa. Perfis e desafios continuam usando seus cards específicos.

A imagem fica em `static/share/chamas-flamejantes-v22-1.jpg`, com acesso público, endereço absoluto e informações de formato, tamanho e descrição. Os metadados são enviados no HTML inicial, seguindo o [protocolo Open Graph](https://ogp.me/), e incluem a prévia grande do Twitter/X.

Para atualizar a capa, inclua também a pasta `static/share`. Preserve o volume e as variáveis existentes do Railway. Envie o link em uma nova mensagem para conferir a prévia; o WhatsApp controla o formato e a atualização das prévias que já armazenou.

Todas as melhorias da V22 abaixo estão incluídas.

## Melhorias da V22

- Navegação em duas linhas alinhadas no computador e menu recolhível no celular, com todas as abas acessíveis.
- Animações de entrada ao rolar, hover dos cards, janelas flutuantes e feedback dos botões. As animações são curtas e respeitam a preferência do aparelho; o rodapé permite reduzi-las.
- Tipografia e espaçamentos consistentes nas páginas públicas, perfis, guias, formulários e painel.
- Perfil compacto com avatar circular, atalhos de navegação, prévia da foto escolhida e contagem de caracteres.
- Alteração de frase e foto sem depender do AoMStats. Marque a opção de atualizar os dados quando quiser sincronizar nome, Elo e foto original.
- Busca de jogadores com contagem e estado vazio; pesquisas adicionais no Elo e nos programas. Busca de mapas preservada.
- Checklist nas build orders, com progresso salvo apenas no navegador utilizado.
- Notificações consultadas a cada 45 segundos com a aba visível. A consulta para ao expirar a sessão e mantém as mensagens anteriores durante falhas de rede.
- Navegação por teclado, foco contido nas janelas de perfil e counters, atalhos Escape e retorno ao controle que abriu o perfil.
- Proteção contra envios repetidos e respostas simultâneas a desafios; cancelamento não reaparece após reiniciar o serviço.
- Estatísticas e sequências de vitórias calculadas em lote, índices para desafios e notificações e catálogo de builds em cache.
- Arquivos estáticos com versão pelo conteúdo, cache e compressão gzip de CSS, JavaScript, JSON e guia HTML. Páginas de conta e tokens não entram em cache compartilhado.
- Fotos novas redimensionadas para até 512 pixels em WebP; limite de 8 MB. Imagens de listas carregadas sob demanda.

Atualize o conteúdo do repositório com este pacote, mantendo as variáveis do Google, a chave secreta e o volume do Railway. A identificação atual em `/health` é `23-arena-publica-cards`.

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
- Fotos circulares nos cards compactos da Arena, sem alterar a estrutura horizontal do card.
- Página pública de perfil redimensionada, com foto e nome proporcionais em desktop e celular.
- O desafiante pode cancelar um pedido ainda pendente; o duelo e sua notificação são removidos imediatamente.
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
