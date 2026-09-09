# Correção de partidas Customs/Quickplay — V22.2

## Causa e correção

A versão anterior consultava apenas `/match/ID`. A partida informada, **43115933**, aparecia em Customs/Quickplay no perfil, embora sua página individual não estivesse disponível. A nova busca consulta a página individual e os históricos recentes com `leaderboard=0` dos dois participantes.

O parser localiza o card pelo ID exato, lê os IDs dos perfis dos dois jogadores e exige um marcador explícito de vitória e outro de derrota. O resultado não depende do nick colorido, da cor do nome, da posição dos jogadores nem da ausência de um ícone. Participantes extras, dados conflitantes e partidas marcadas como dessincronizadas são rejeitados. O formato serializado de partidas também é lido sem executar scripts externos.

Em partidas Customs/Quickplay, o botão de origem abre o histórico do perfil em que o resultado foi encontrado, evitando encaminhar para a página individual inexistente.

## Carregamento e correção do ID

- Prazo de 12 segundos para coletar as respostas externas, com limites por conexão/leitura e máximo de 3 MB por página. Há no máximo seis tarefas externas simultâneas por processo, sem fila ilimitada.
- O navegador interrompe a espera após 20 segundos e restaura os controles mesmo se a conexão falhar ou a sessão expirar.
- Nenhuma consulta de partida se repete automaticamente. Cada clique tem fim e informa o estado encontrado.
- O estado pendente passa a ser “Resultado não confirmado”, e o ID pode ser corrigido antes da confirmação.
- A barra de leitura do topo fica oculta nas páginas de duelo para não ser confundida com a consulta.
- O resultado só é aplicado se o duelo ainda estiver pendente com o mesmo ID. Submissões repetidas não duplicam a notificação do mesmo ID.

## Evidência e testes

Em 09/09/2026, foi observado no [histórico público Customs/Quickplay](https://aomstats.io/profile/1076869557?leaderboard=0):

| Campo | Valor |
| --- | --- |
| ID | 43115933 |
| Mapa | Mirage |
| Duração | 6:08 |
| Vencedor | Makise_Kurisu_00 — perfil 1076869557 |
| Derrotado | Andre3rr — perfil 1076393730 |

Também foi capturado um card da [partida ranqueada 38263962](https://aomstats.io/match/38263962), para preservar compatibilidade. Esses trechos estão em `tests/fixtures`.

**30 testes Python e 3 testes JavaScript passaram**, incluindo os dois cards reais, gravação do vencedor, consultas que não respondem, resultados ausentes, ID corrigido, permissões, CSRF, conflito entre alterações simultâneas, formulários liberados após erro e os testes anteriores do site.

```bash
python -m unittest discover -s tests -v
node --test tests/duel_ui.test.cjs
```

As consultas de rede nos testes são simuladas com o HTML capturado. O domínio de produção não foi alterado e não foi executado um duelo real pelo Railway. A disponibilidade do AoMStats e eventuais mudanças no HTML continuam sendo dependências externas. A busca dos perfis cobre as partidas recentes presentes no HTML inicial, sem percorrer indefinidamente todo o histórico. Se o jogo for muito antigo, pode ser necessário informar outro ID recente.

## Atualização

Substitua os arquivos do GitHub com o pacote completo. Preserve o volume do banco, uploads e variáveis do Railway. Quando `/health` indicar `22.2-partidas-customs`, abra o duelo que já contém o ID e use **Verificar novamente**. Não é necessário recriar o desafio.
