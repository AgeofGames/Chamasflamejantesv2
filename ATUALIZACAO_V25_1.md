# V25.1 — piso zero, sem dívida de pontos

A Arena agora desconta derrotas somente até zero. Não existe dívida para recuperar antes de voltar a pontuar.

| Situação | Pontuação após a partida |
| --- | ---: |
| Zero pontos e outra derrota | 0 |
| 10 pontos e derrota normal de −20 | 0 |
| Zero pontos e vitória normal | 30 |
| Zero pontos e vitória com bônus de +90 | 90 |
| Zero pontos e vitória com bônus de +120 | 120 |

Mesmo com **1 vitória e 7 derrotas no histórico**, se o jogador está com zero e ganha uma partida normal, fica com **30 pontos**. O histórico passa a mostrar 2 vitórias e 7 derrotas.

O cálculo considera a ordem das partidas. Por exemplo, seis vitórias e depois quatro derrotas dão 100 pontos; quatro derrotas a partir de zero e depois seis vitórias dão 180. Não há desconto retroativo das derrotas que ocorreram em zero. Os bônus e perdas por diferença de Elo continuam com as mesmas faixas.

## Correção automática

Na primeira inicialização da V25.1, a temporada corrente é recalculada pela ordem dos registros confirmados. Cada derrota para em zero e cada vitória acrescenta seu ganho integral. Isso corrige tanto saldos negativos quanto vitórias que a V25 havia usado para compensar dívidas.

Os resultados, vitórias, derrotas, IDs, adversários, bônus registrados e progresso dos emblemas são preservados. Meses encerrados e suas conquistas permanecem intactos. O extrato da temporada corrente passa a mostrar o desconto real: se havia 10 pontos, uma derrota de regra −20 aplica apenas −10.

A migração registra `arena_v25_1_migrated` e não reaplica a correção a cada reinício. Antes de alterar os saldos, conserva as tabelas `arena_standings_before_v25_1` e `arena_results_before_v25_1` para conferência.

## Atualização no GitHub/Railway

Este ZIP contém o site completo, incluindo notificações automáticas, limites de desafios, bônus por Elo, fotos e emblemas.

1. Envie o conteúdo do ZIP ao repositório que já está conectado ao Railway.
2. Preserve banco SQLite, volume, uploads e variáveis atuais.
3. Aguarde o deploy. `/health` deve mostrar **25.1-piso-zero**.

Pode atualizar diretamente da V24.2 ou da V25. As migrações necessárias são automáticas. O pacote foi preparado e testado localmente; a implantação no servidor do usuário não foi executada pelo assistente.

## Verificação

85 testes Python e 20 JavaScript. Incluem: piso zero em X1, duplas e trios; exemplo de 1 vitória e 7 derrotas seguido de uma vitória; perda parcial até zero; bônus integral a partir de zero; correção da dívida da V25; preservação de resultados, emblemas e meses encerrados; reinicialização sem pontuar novamente; apresentação dos descontos reais no extrato.

Consultas ao Google e ao AoMStats são simuladas nos testes. Para repetir: `python -m unittest discover -s tests -v` e `node --test tests/*.test.cjs`.
