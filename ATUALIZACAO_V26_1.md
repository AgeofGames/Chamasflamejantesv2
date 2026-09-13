# V26.1 — Perfil compacto e remoções

Registro da versão anterior. Para a organização atual do perfil e as instruções desta entrega, consulte **ATUALIZACAO_V26_2.md**.

## Removido

- Mural da comunidade, publicações de vitória/estratégia/novidade, curtidas e comentários do mural.
- Coleção pessoal de build orders, favoritas e anotações.
- Links desses recursos no menu, perfil, catálogo e duelos. Avisos antigos do mural deixam de aparecer nas notificações.
- Faixa larga e separada de ações que aparecia abaixo dos cards do perfil.

Os endereços antigos do mural e das favoritas retornam 404, inclusive para ações enviadas diretamente. A atualização não apaga registros antigos do banco: eles ficam sem acesso público, preservando a compatibilidade com os comentários de replays e o histórico existente.

## Perfil

| Área | Apresentação atual |
| --- | --- |
| Capa | Botão **Escolher capa** no card **Este perfil é seu**, junto aos demais controles. A seleção abre somente ao clicar. Foto redonda e fundo escolhido continuam no card de identidade e na janela flutuante. |
| Conquistas | Três linhas compactas, com ícone pequeno, nome, descrição e progresso. Ficam dentro da coluna do perfil, com opção de recolher. |
| Evolução | Card recolhido inicialmente. Clique no título para ver o gráfico, selecionar temporada/modalidade ou consultar o extrato. O gráfico tem altura limitada e acompanha a largura do card. |
| Rivalidades | Card recolhido inicialmente, com placar e links para os confrontos. A lista de muitos adversários tem rolagem própria. A página de rivalidade completa também tem largura menor. |

As três áreas ficam na mesma coluna de **Números na Arena**, **Este perfil é seu** e **Compartilhar perfil**, dentro da largura já usada pelos cards. Não existe mais um cabeçalho largo de jornada ocupando a página inteira. No celular, os cards acompanham a largura disponível.

Ao abrir um link diretamente em `#evolucao` ou `#rivalidades`, a seção correspondente se expande. Escolher outro mês ou modalidade também mantém a evolução aberta.

## Preservado

Pontuação +30/−30 e bônus por Elo, piso zero, limites de desafios, ranking completo, temporadas e dez emblemas, conquistas já obtidas, tag “Mais desafiado”, dupla no perfil, fotos, histórico de vitórias/derrotas/fugas, compartilhamento externo de resultados, agendamentos e notificações.

Também permanecem a luz verde de presença, ID da partida detectada e botão **Copiar ID**, assim como envio/download de replays e os comentários de análise nos replays. As build orders normais e seus checklists continuam no catálogo.

## Atualizar

1. Extraia o ZIP e envie o conteúdo completo ao repositório conectado ao Railway, incluindo `community_hub.py`, templates e arquivos `static`.
2. Preserve banco, volume, fotos, pasta `arena_replays` e variáveis do serviço. Não há novas credenciais ou configuração obrigatória.
3. Aguarde a implantação ativa. `/health` deve informar `26.1-perfil-compacto`.
4. Abra o próprio perfil e confira **Escolher capa**, as conquistas pequenas e os cards de evolução e rivalidades. Os avisos antigos do mural não reaparecem.

Os templates de mural e favoritas foram retirados do ZIP. Mesmo se cópias antigas ainda estiverem no repositório, as rotas e os acessos foram removidos do aplicativo atualizado.

## Validação

- 134 testes Python e 36 JavaScript passaram, com banco isolado e Google/AoMStats simulados.
- Verificados: rotas removidas, menus, notificações antigas, preservação de registros, comentários e paginação dos replays, pontuação, partidas, equipes, agendamentos, presença e cópia de ID.
- Inspeção em Chromium nas larguras 1920, 1024, 768 e 390 px. A jornada ficou com 734, 654, 428 e 358 px, respectivamente, sempre dentro da coluna do perfil, sem rolagem horizontal.
- Gráfico, expansão dos cards, links de seções e botão de capa funcionaram sem erros de JavaScript nessa conferência.

O pacote precisa ser publicado no GitHub/Railway pelo responsável pelo site.
