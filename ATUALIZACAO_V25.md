# Chamas Flamejantes V25 / V25.1 — pontos, desafios e notificações

A V25.1 aplica piso zero sem dívida. Leia também ATUALIZACAO_V25_1.md.

## Publicação

Este ZIP contém o site completo, baseado na V24.2, com os dez emblemas, fotos redondas, torneios, compartilhamento e integração de partidas preservados.

1. Extraia o ZIP e envie seu conteúdo ao repositório que já está conectado ao Railway, incluindo `arena_rules.py`, `arena_seasons.py`, `arena_teams.py`, `app.py`, `templates` e `static`.
2. Mantenha o banco SQLite, o volume, os uploads e as variáveis atuais. O ZIP não inclui um banco para substituir seus dados.
3. Aguarde a implantação. A migração é automática na primeira inicialização da V25.
4. Confira `/health`: a versão deve ser `25.1-piso-zero`.

Não há novas credenciais nem serviço adicional para configurar. O pacote foi testado localmente; a implantação no seu GitHub/Railway não foi executada pelo assistente.

## Pontuação

O Elo usado para comparar os adversários é o Elo do AoMStats mostrado na Comunidade. Os ganhos e perdas entram no ranking mensal da Arena; não modificam o Elo oficial do jogo.

| Diferença de Elo | Vitória do menor Elo | Derrota do maior Elo |
| --- | ---: | ---: |
| Até 100, inclusive | +30 | −20 |
| Maior que 100 e menor que 200 | +90 | −90 |
| 200 a menos de 300 | +120 | −120 |
| 300 a menos de 400 | +150 | −150 |
| Cada nova faixa de 100 | +30 de bônus adicional | −30 de perda adicional |

Se o jogador de Elo maior ou igual vencer, recebe +30 e o derrotado perde 20, independentemente da diferença. O bônus exige vitória do jogador de Elo menor e diferença superior a 100.

Exemplos: 1099 vence 1200 → +90/−90; 1000 vence 1200 → +120/−120; 1100 vence 1200 → +30/−20. A regra de bloqueio abaixo sempre prevalece: bônus não autoriza um confronto proibido.

O Elo fica registrado no envio do desafio. Em duplas e trios, o cálculo usa a média do Elo de equipe; todos do mesmo lado recebem os mesmos pontos. Sem Elo conhecido de algum integrante, vale a regra base, sem bônus. Desafios que estavam ativos na atualização usam o Elo registrado na migração.

Cada duelo concluído tem um extrato público com o ganho/perda de cada jogador e o saldo após a partida. O perfil também mostra o ganho/perda em cada confronto X1.

## Correção do saldo e dos emblemas

Com a regra base, **6 vitórias seguidas e depois 4 derrotas = 100 pontos**. Na V25.1, cada partida é calculada na ordem da confirmação, com piso zero real: derrotas não deixam dívida. Em zero, a próxima vitória normal já dá 30 pontos, e os bônus por Elo continuam integrais. O extrato mostra o desconto efetivamente aplicado quando a derrota ultrapassaria os pontos disponíveis. Não há descarte de pontos ao chegar a 999.

O progresso do emblema é separado do saldo. Os ganhos e perdas também movimentam esse progresso, limitado entre Brasa e Imortal. Três derrotas seguidas ou quatro acumuladas podem rebaixar o emblema, sem tirar pontos adicionais do ranking. Se a própria derrota já causar o rebaixamento, não existe uma segunda queda. Os contadores reiniciam após o gatilho. Vitórias zeram a sequência, mas mantêm as derrotas acumuladas. O perfil informa o progresso necessário para recuperar o próximo emblema.

Na virada do mês de Brasília, cada modalidade começa com saldo e progresso zero. A conquista do mês encerrado permanece no perfil, assim como os históricos de jogos, adversários, IDs, vitórias, derrotas e recusas.

## Limites

- Três solicitações por par de adversários ao dia, somando os dois sentidos e as modalidades X1/duplas/trios.
- Solicitações recusadas e canceladas consomem a tentativa. Cancelar continua removendo o desafio da tela, mas não libera a cota.
- Em equipes, cada par de jogadores em lados opostos consome uma tentativa; mudar de equipe não contorna o limite.
- O dia muda à meia-noite de Brasília. Desafios apagados antes da V25 não têm registros que permitam reconstruir sua contagem.
- Jogadores com Elo **1300 ou mais** não podem desafiar nem receber desafio de adversários com Elo **1000 ou menos**, incluindo 800 e abaixo. Para esse confronto, o menor Elo deve estar conhecido e acima de 1000.
- Em equipes, o bloqueio verifica cada par de adversários pelo Elo de equipe; a média não esconde jogadores fora da faixa permitida.
- Os limites são verificados no servidor, dentro da transação de criação do desafio. O perfil mostra o motivo do bloqueio e a cota disponível.

## Notificações automáticas

A lista e o contador consideram desafios ativos. Quando um duelo é concluído, recusado ou cancelado, suas mensagens deixam de aparecer nas notificações. Os registros de jogos e resultados não são apagados.

Com a página visível, o navegador consulta a caixa a cada 3 segundos, sem recarregar a página. Ao voltar para a aba ou recuperar a conexão, faz uma consulta imediata. Abas ocultas param as consultas. Uma falha de rede aplica uma pausa progressiva e a próxima tentativa recupera a lista; não são abertos pedidos simultâneos. Uma consulta sem mudanças recebe uma resposta curta, sem renderizar novamente as mensagens.

Esse comportamento é atualização automática dentro do site aberto, não uma notificação do sistema com o navegador fechado.

## Migração

A migração acontece uma vez e fica registrada em `site_meta.arena_v25_migrated`. O saldo da temporada corrente é reconstruído em ordem de confirmação a partir dos resultados já registrados. Como as versões anteriores não guardavam Elo por duelo, esses jogos usam +30/−20; não se calcula um bônus retroativo usando o Elo atual. Temporadas anteriores, premiações e todos os duelos permanecem intactos.

Antes de recalcular, o banco conserva as tabelas de pontuação anteriores em `arena_standings_before_v25`, `arena_results_before_v25` e `arena_awards_before_v25`. Elas são uma cópia para conferência da pontuação anterior, não substituem uma cópia completa do volume.

## Validação

- 85 testes Python e 20 JavaScript, em banco isolado e sem serviços externos reais.
- Migração a partir das tabelas da V24: o caso de 129 pontos, com uma derrota inicial, cinco vitórias, três derrotas e mais uma vitória, passa a 120 com o piso zero da V25.1, sem modificar os duelos.
- Limites 100/101/199/200/299/300, bônus simétrico, Elo registrado por desafio e pontuação base do vencedor favorito.
- Limites diários nos dois sentidos, cancelamento, modalidades compartilhadas, fronteira de Brasília e concorrência pela última vaga.
- Proteção 1300/1000, confronto invertido, Elo desconhecido e proteção contra médias de equipe que escondem adversários proibidos.
- Notificações privadas, remoção de partidas antigas antes da paginação, contador correto e histórico preservado.
- Chegada em 3 segundos, retomada ao voltar à aba, falhas de rede, limite de tempo e preservação de foco do teclado.
- Regressão dos fluxos anteriores: login simulado, AoMStats/Customs com fixtures, imagens, torneios, perfis, equipes e temporadas.

Para repetir: `python -m unittest discover -s tests -v` e `node --test tests/*.test.cjs`.
