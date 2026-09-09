# V22.3 — Capa no WhatsApp e logo nas pesquisas

## Diagnóstico observado

Em 09/09/2026, a página pública `https://chamasflamejantes.com.br/` declarava a capa da V22.1 em `og:image`, `og:image:secure_url` e `twitter:image`. A imagem abriu no navegador sem login, com 1200 × 630 pixels. A descrição publicada era “Build orders, torneios, mapas e duelos na Arena X1. Faça parte da comunidade Chamas Flamejantes!”.

A captura do WhatsApp exibia a descrição anterior. Isso indica uma prévia armazenada, sem confirmar por si só como o robô do WhatsApp acessou o site. Nenhum favicon estava declarado no cabeçalho publicado.

## O que foi alterado

- A chama da identidade visual foi adaptada para um ícone vetorial e exportada em PNG 512 × 512, PNG 96 × 96, Apple Touch 180 × 180 e ICO com sete resoluções (16 a 256 pixels).
- Os ícones são declarados no HTML compartilhado por todas as páginas. Suas URLs públicas permanecem estáveis, sem query string de versão.
- A capa existente ganhou um endereço direto e público: `/capa-chamas-flamejantes.jpg`. O arquivo original continua incluído para manter links anteriores.
- `/compartilhar` serve a mesma página inicial, sem redirecionamento, mantendo os torneios, ranking e navegação. Seu `og:url` é próprio; `rel=canonical` aponta para `/`.
- O botão **Compartilhar site** no rodapé utiliza esse endereço novo por meio do compartilhamento nativo ou da cópia do link já existente no projeto.
- As imagens não acessam banco de dados, não exigem sessão e respondem a GET, HEAD e requisições condicionais com MIME e cache adequados.
- A V22.2 está integralmente incluída, incluindo a confirmação de partidas Customs/Quickplay e o limite de tempo das consultas.

## Atualizar e conferir

1. Envie os arquivos do ZIP ao GitHub, incluindo `static/brand` e `static/share`. Preserve as variáveis e o volume existentes do Railway.
2. Aguarde o Railway mostrar a implantação ativa. O endpoint `/health` deve retornar a versão `22.3-whatsapp-favicon`.
3. Abra `/favicon.png` e `/capa-chamas-flamejantes.jpg` no domínio do site: devem mostrar a chama e a capa, respectivamente.
4. No WhatsApp, envie uma mensagem nova usando `https://chamasflamejantes.com.br/compartilhar`. Aguarde o aplicativo montar a prévia antes de enviar.
5. No Google Search Console, inspecione `https://chamasflamejantes.com.br/` e solicite indexação.

O Google informa que uma nova leitura pode levar dias ou semanas e que a exibição do favicon não é garantida. Não é preciso alterar o domínio na Hostinger para instalar esses arquivos.

## Validação e limites

Passaram 32 testes Python e 3 testes JavaScript. A validação incluiu metadados renderizados no servidor, integridade e dimensões dos ícones, acesso sem banco/sessão, permissões de rastreamento em `robots.txt`, comportamento do link novo e preservação dos cards de perfil e convite. As consultas externas de duelos foram simuladas nos testes.

O pacote não foi publicado no GitHub/Railway por este assistente. A atualização efetiva de caches e o desenho da prévia são controlados por WhatsApp e Google; não há garantia de atualização instantânea nem de alteração das mensagens antigas.

Referências: [Google Search Central — favicons](https://developers.google.com/search/docs/appearance/favicon-in-search) e [Open Graph — propriedades de imagem](https://ogp.me/#structured).
