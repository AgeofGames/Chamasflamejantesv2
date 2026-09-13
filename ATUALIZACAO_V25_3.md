# V25.3 — correção dos pontos já registrados

A V25.2 aplicava a derrota padrão de −30 somente aos novos resultados. Os resultados anteriores com −20 continuavam produzindo saldos como **5 vitórias, 1 derrota e 130 pontos**. Faltava atualizar a pontuação já registrada da temporada em disputa.

A V25.3 faz esse recálculo automaticamente, uma única vez na inicialização, para **X1, duplas e trios**.

## Caso corrigido

| Sequência sem bônus | Saldo anterior, com derrota de −20 | Saldo corrigido, com derrota de −30 |
| --- | ---: | ---: |
| 5 vitórias, depois 1 derrota | 130 | **120** |
| 6 vitórias, depois 4 derrotas | 100 | **60** |
| 1 derrota em zero, depois 5 vitórias | 150 | **150** |
| 1 vitória, 7 derrotas, depois 1 vitória | 30 | **30** |

O piso zero continua sem dívida. Por isso o sistema percorre as partidas na ordem de confirmação; não calcula o saldo apenas multiplicando os totais de vitórias e derrotas.

## Preservação dos dados

- As derrotas padrão antigas de −15 ou −20 passam a −30 na temporada atual. As vitórias e os bônus já registrados são preservados.
- A diferença de Elo é a registrada na época do resultado. O Elo atual do perfil não é usado para inventar ou alterar bônus antigos.
- O saldo e o progresso atual dos emblemas são reconstruídos com o mesmo cálculo usado nos novos resultados. Três derrotas seguidas ou quatro acumuladas continuam rebaixando o emblema, sem desconto extra de pontos do ranking.
- O extrato passa a mostrar os valores corrigidos antes e depois de cada partida. Os IDs, adversários, vencedores, datas e registros dos duelos permanecem.
- Meses anteriores encerrados e emblemas já conquistados mantêm seus valores originais.
- Duplas, notificações, tag “Mais desafiado”, fotos, limites e restrições de Elo permanecem.

Antes da alteração, o banco guarda as cópias `arena_results_before_v25_3` e `arena_standings_before_v25_3` da temporada atual. A marca `arena_v25_3_migrated` impede que a correção se repita nos próximos reinícios. O recálculo, as cópias e a marca são gravados na mesma transação: se houver falha, nenhuma correção parcial é confirmada.

## Publicação

1. Envie o conteúdo completo deste ZIP ao GitHub conectado ao Railway.
2. Preserve o banco SQLite, o volume, as fotos e as variáveis existentes.
3. Aguarde o deploy e a inicialização. A correção será automática; não é necessário reenviar IDs ou resultados.
4. `/health` deverá mostrar **25.3-correcao-pontos**. Abra o ranking novamente após o deploy.

Este é o pacote completo, com as atualizações anteriores incluídas. A publicação no servidor do usuário não foi executada pelo assistente.

## Validação

**103 testes Python e 20 JavaScript passaram**, com serviços externos simulados. O caso de Makise foi reproduzido em banco de teste existente: 5 vitórias e 1 derrota, saldo de 130 antes e 120 após a atualização, conferido no ranking, no perfil, na janela flutuante e no extrato.

Também foram verificados o piso zero nas três modalidades, os bônus com Elo histórico, a preservação de meses encerrados, as regras dos emblemas, a repetição de resultados sem pontos duplicados, reinícios e a reversão integral diante de uma falha simulada durante a migração.

```bash
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
```
