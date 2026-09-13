# V27 — SEO e Google Search Console

## O que foi preparado

- Títulos e descrições próprios para as páginas públicas: início, torneios, resultados, rankings, perfis, equipes, rivalidades, replays, mapas, programas e guias.
- As **113 build orders** e as páginas dos **23 deuses** têm metadados de acordo com seu conteúdo.
- Endereço principal (`canonical`) consistente, usando o domínio configurado em `PUBLIC_BASE_URL`. Parâmetros de campanha não criam novos endereços principais. A paginação mantém endereços próprios para que os registros antigos sejam encontrados.
- Dados estruturados de site, comunidade, páginas e navegação. Nome do Chamas Flamejantes e logo identificados na página inicial.
- Sitemap ampliado com equipes formadas, resultados confirmados, rivalidades e replays públicos, além das seções, torneios, guias e perfis. Temporadas e modalidades possuem endereços próprios. A divisão em vários sitemaps é automática quando necessária.
- Datas de modificação usadas apenas quando há um registro válido; o acesso ao sitemap não inventa uma atualização do conteúdo.
- Login, administração, notificações, agenda pessoal, edição de perfil, fragmentos de janelas, APIs e erros recebem instruções para não serem indexados. Páginas de resultados ainda não confirmados e variações de filtros também não entram como conteúdo principal da busca.
- CSS, JavaScript, favicon, logo e imagens públicas continuam acessíveis aos rastreadores. Os cards de compartilhamento de perfis, desafios, vitórias e torneios são preservados.
- **Mapa do site** no rodapé, com links para as seções e todas as build orders. A página inicial ganhou atalhos para os guias, e o Guia de Teclas recebeu título e introdução no HTML da própria página.
- Área **Google / SEO** no painel administrativo para configurar a verificação do Search Console.

O objetivo é facilitar a descoberta e a compreensão do conteúdo. O Google decide a indexação e a posição das páginas; a atualização não garante aparecer imediatamente nem ocupar uma posição específica. [Guia oficial de SEO do Google](https://developers.google.com/search/docs/fundamentals/seo-starter-guide).

## Publicar

1. Extraia o ZIP e envie o conteúdo completo ao GitHub conectado ao Railway, incluindo **site_seo.py**, templates e `static`.
2. Preserve banco, volume, fotos, replays e variáveis atuais.
3. Mantenha `PUBLIC_BASE_URL=https://chamasflamejantes.com.br`. Essa variável passa a ser a referência única para os endereços públicos. `SEO_BASE_URL` continua aceito como alternativa quando `PUBLIC_BASE_URL` não está definido.
4. Aguarde a implantação. `/health` deverá informar **27.0-seo-google**.

Esta versão não altera as regras de pontos ou a disposição do perfil. O card **Com quem jogou** mantém a mesma largura do card acima. A configuração opcional do Google é salva na tabela de configurações já existente; não é necessário substituir ou apagar o banco.

## Ativar no Google Search Console

### Se o site já estiver verificado

Abra a propriedade correta no [Search Console](https://search.google.com/search-console), acesse **Sitemaps** e envie:

```text
https://chamasflamejantes.com.br/sitemap.xml
```

O envio do sitemap ajuda o Google a descobrir muitas páginas de uma vez. O arquivo acompanha novos conteúdos públicos automaticamente; não é preciso reenviar cada perfil ou partida manualmente. [Documentação de sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap).

### Se ainda não estiver verificado

1. No Search Console, adicione uma propriedade do tipo **Prefixo do URL** com `https://chamasflamejantes.com.br/`.
2. Escolha **Tag HTML** e copie a meta tag fornecida pelo Google.
3. No site, entre como administrador e abra **Painel → Google / SEO**.
4. Cole a meta tag ou apenas o código e clique em **Salvar código**.
5. Volte ao Search Console e clique em **Verificar**. Depois, envie o sitemap acima.

Se você já usa uma propriedade de **Domínio** verificada por DNS, continue com ela. A tag HTML é uma alternativa para propriedades de prefixo de URL. [Verificação oficial de propriedade](https://support.google.com/webmasters/answer/9008080?hl=pt-BR).

Como alternativa ao painel, o valor do atributo `content` da tag pode ser definido em `GOOGLE_SITE_VERIFICATION` no Railway. Quando essa variável estiver preenchida, ela tem prioridade sobre o painel. O site informa apenas se o código está configurado; a confirmação da propriedade ocorre no Google.

### Após enviar o sitemap

Na **Inspeção de URL**, teste a página inicial e os principais guias. Se o teste do endereço publicado estiver correto, use **Solicitar indexação**. Acompanhe depois os relatórios **Páginas** e **Desempenho**. O rastreamento pode levar dias ou semanas; repetir a solicitação da mesma URL não acelera o processo. [Orientação oficial sobre novo rastreamento](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl).

As exclusões de login, administração e filtros são intencionais. Resultados e cadastros permanecem acessíveis no site conforme as permissões existentes.

## Validação

- **145 testes Python passaram**, incluindo 11 novos testes de SEO.
- Rastreamento local das páginas do sitemap: resposta 200, título, descrição, endereço principal, dados estruturados e permissão de indexação.
- Verificação de acesso privado, páginas inexistentes, proteção do formulário administrativo, paginação, integridade do histórico e imagens de compartilhamento.
- Conferência no navegador em computador e celular: painel de configuração, mapa do site, guias e alinhamento do histórico no perfil, sem transbordamento horizontal.
- As integrações Google/AoMStats foram simuladas, com banco isolado. A validação local não representa confirmação de indexação na conta do Search Console.

Referências técnicas adicionais: [endereços principais](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls), [paginação](https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading), [nome do site](https://developers.google.com/search/docs/appearance/site-names) e [navegação estruturada](https://developers.google.com/search/docs/appearance/structured-data/breadcrumb).
