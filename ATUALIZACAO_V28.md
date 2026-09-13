# V28 — Equilíbrio da Arena Customs/Quickplay

Este pacote completo atualiza a V27. A pontuação alterada é a do ranking mensal da Arena; o Elo ranqueado oficial do AoMStats não é modificado.

## Regra implementada

Quando o jogador de menor Elo vence, o benefício exige:

- Elo menor **abaixo de 1000** e adversário com **1000 ou mais**, conforme o Elo registrado no desafio.
- Pelo menos **8 partidas ranqueadas concluídas no mês** para o menor Elo, comprovadas por registros do AoMStats.

| Diferença de Elo | Ganho do menor Elo vencedor | Perda do maior Elo derrotado |
| --- | ---: | ---: |
| Até 100 | +40 | −40 |
| Acima de 100 até 200 | +50 | −50 |
| Acima de 200 | +50 | −50 |

A faixa de 101 a 199 segue a faixa “até 200”. O limite permanece 50 para qualquer diferença maior. O piso zero continua: quem tem 20 pontos e perde 50 fica com zero, sem dívida para a próxima vitória.

Se o maior Elo vencer, vale +30/−30. Quando os requisitos não são cumpridos ou não podem ser comprovados, continua a fórmula padrão da V27, incluindo os bônus anteriores por diferença de Elo. Por exemplo, dois jogadores de 1000 e 1200 continuam sujeitos à fórmula padrão, pois o menor não está abaixo de 1000.

No X1, vale o Elo 1×1. Em duplas e trios, permanece o Elo médio de equipe registrado por lado, e **cada integrante do lado de menor Elo** deve comprovar as 8 ranqueadas. Todos do mesmo lado recebem a mesma pontuação.

## Atividade mensal

O mês segue Brasília e a temporada em que o resultado foi registrado na Arena, preservando o calendário usado pela V27. As modalidades ranqueadas Sup 1v1, Sup Team, DM 1v1 e DM Team contam juntas; o mesmo ID de partida conta uma só vez por perfil. Customs/Quickplay, partidas em andamento, resultados não confirmados e totais acumulados do perfil não comprovam atividade ranqueada mensal.

Ao completar as oito ranqueadas, os resultados elegíveis registrados anteriormente no mesmo mês também podem ser corrigidos. A atividade de um mês não libera o benefício no mês seguinte.

O site consulta as páginas públicas de partidas do AoMStats e guarda os IDs, as datas, a modalidade e a fonte de cada comprovação. Antes de pontuar uma vitória candidata, consulta a atividade quando necessário. Há também uma verificação em segundo plano, com cache compartilhado pelos workers do Railway e novas tentativas automáticas. As consultas de rede acontecem fora da transação que atualiza o ranking.

**Limite da fonte:** o histórico visível nas páginas públicas do AoMStats pode não incluir todas as partidas antigas. Não é correto concluir que o jogador jogou menos de oito apenas porque esses registros não foram encontrados. Sem comprovação suficiente, a partida permanece pendente, com sua pontuação original. Falhas de rede não criam atividade nem apagam comprovações já guardadas. O site não inventa Elo ou identidades antigas a partir do perfil atual.

Referência dos campos e das modalidades: [documentação de dados do AoMStats](https://aomstats.io/api). A estrutura de registros públicos foi conferida com HTML obtido do [perfil ranqueado usado no projeto](https://aomstats.io/profile/1076869557?leaderboard=1).

## Revisão do histórico

Na primeira inicialização, o site guarda cópias da pontuação existente:

- `arena_results_before_v28`: extratos anteriores.
- `arena_standings_before_v28`: saldos e progresso dos emblemas.
- `arena_awards_before_v28`: posições e conquistas dos meses encerrados.

As partidas candidatas de todo o histórico entram na revisão. Quando a atividade mensal é comprovada, o sistema corrige o ganho e a perda juntos, grava o extrato original e as evidências em `arena_balance_adjustments`, e reconstrói a classificação afetada na ordem original de confirmação. Os ganhos e perdas das outras partidas não são substituídos; seus saldos anteriores e posteriores acompanham a correção.

A revisão também contempla meses encerrados elegíveis: atualiza seus pontos, emblemas e posições, preservando a data de encerramento. Jogadores, vencedores, perdedores, IDs, datas e Elo registrado dos duelos permanecem intactos. Um reinício ou uma nova consulta não aplica a correção duas vezes. Se houver falha durante o recálculo, a transação é revertida integralmente.

O painel **Pontos da Arena**, em `/admin/arena-pontos`, mostra benefícios aplicados, partidas aguardando comprovação e resultados sem identidade histórica suficiente. O botão **Verificar novamente** coloca as consultas na fila. A página é exclusiva do administrador.

## Atualizar no Railway

1. Faça o backup do SQLite pelo painel e preserve o volume existente.
2. Extraia este ZIP e atualize o conteúdo completo do projeto no GitHub conectado ao Railway, incluindo `arena_balance.py`, `aomstats_activity.py`, os templates e os demais arquivos.
3. Mantenha `DATABASE_PATH`, `FFA_SECRET_KEY`, `PUBLIC_BASE_URL`, configurações Google, uploads, fotos e replays existentes. **Não substitua nem apague o banco de produção.**
4. Aguarde a inicialização. `/health` deverá mostrar **28.0-equilibrio-arena**.
5. Abra **Painel → Pontos da Arena** para acompanhar a revisão automática. Confira os extratos dos duelos e os rankings.

Não há dependências novas. `ARENA_ACTIVITY_ENABLED=0` desliga a verificação em segundo plano para testes; em produção, deixe essa variável ausente ou use `1`.

O ZIP não contém o banco de produção. Portanto, os números reais de partidas corrigidas serão conhecidos somente depois de instalar o pacote no servidor e verificar as evidências disponíveis. A publicação no Railway não foi executada nesta entrega.

## Validação

**159 testes Python e 36 testes JavaScript passaram**, em banco isolado, com integrações externas simuladas. Foram conferidos os limites 100/101/199/200/201/300, a atividade mensal, a virada do mês de Brasília, a identidade histórica, duplas, piso zero, saldos posteriores, meses encerrados, auditoria, reinícios, falha com reversão integral e os controles de acesso do painel. O fluxo de envio de resultado foi testado com consulta de atividade simulada e conferência do extrato público.

```bash
python -m unittest discover -s tests
node --test tests/*.test.cjs
```
