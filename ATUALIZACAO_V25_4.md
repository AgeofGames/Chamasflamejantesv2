# V25.4 — presença do Age pelo AoMStats

A foto recebe uma luz verde brilhante quando o ID AoMStats vinculado ao jogador aparece nas listas públicas de atividade. A indicação fica na Arena X1, nos rankings, no Elo da Comunidade, nos perfis completos e flutuantes, nas equipes e no avatar do cabeçalho.

| Evidência no AoMStats | Indicação no perfil |
| --- | --- |
| Jogador em uma sala aberta | Luz verde · Em sala no Age |
| Jogador em uma partida ranqueada ou Customs em andamento | Luz verde · Em partida no Age |
| Nenhuma confirmação válida | Sem luz · Presença no Age não confirmada |

Abra o perfil ou passe o cursor sobre a foto para consultar a indicação. A presença se atualiza automaticamente enquanto a página está aberta. Fotos redondas, nomes coloridos e emblemas continuam com o tamanho e a posição anteriores.

## O que a luz significa

A fonte são as páginas públicas [Ranqueadas](https://aomstats.io/lobbies), [Customs](https://aomstats.io/lobbies/customs) e [Salas abertas](https://aomstats.io/lobbies/open) do AoMStats. O sistema compara IDs numéricos; apelidos iguais, histórico antigo, adversários de desafios, IA e vagas abertas não ativam presença.

Estar no menu do jogo, estar conectado ao Steam ou estar navegando neste site não confirma presença nessas listas. Por isso a ausência da luz não significa necessariamente que a pessoa está offline. A indicação também depende da disponibilidade e da atualização dos dados públicos do AoMStats; não é uma conexão direta com o jogo.

Não é necessário configurar chave Steam, mudar o login Google ou cadastrar novamente os jogadores.

## Atualização e desempenho

- O navegador verifica a presença a cada 20 segundos, pausa consultas em abas ocultas e verifica novamente quando a pessoa retorna à página ou recupera a conexão.
- Cada lista pública é consultada no máximo uma vez a cada 45 segundos para todo o servidor, com cache e bloqueio temporário compartilhados pelos dois workers do Railway. O número de consultas externas não cresce com a quantidade de fotos exibidas.
- As páginas abrem sem esperar pelo AoMStats. A consulta acontece depois, em uma única chamada para todas as fotos.
- Uma confirmação vale no máximo 90 segundos localmente. Também é verificada a data da fonte: nenhum snapshot com três minutos ou mais é aceito. Consultas que falham não renovam confirmações antigas.
- Quando uma nova lista válida já não contém o jogador, a luz correspondente é removida na atualização. Se houver falha de rede, ela expira automaticamente. A atualização depende desses intervalos e da frequência do próprio AoMStats.
- As requisições têm limite de tempo e tamanho, sem repetir chamadas simultâneas à mesma lista. O brilho é contínuo e leve, sem animação permanente nem bibliotecas novas.

## Instalação

1. Envie o conteúdo completo do ZIP ao GitHub conectado ao Railway, incluindo `aom_presence.py`, os templates e os arquivos de `static`.
2. Preserve o volume, o banco SQLite, as fotos e as variáveis existentes.
3. Aguarde o deploy. `/health` deverá indicar **25.4-presenca-aomstats**.
4. Ao abrir novamente a Arena ou um perfil, os indicadores passam a atualizar sem recarregar a página.

A tabela de cache `aom_presence_cache` é criada automaticamente. A atualização mantém os pontos e resultados da V25.3: vitória padrão +30, derrota padrão −30, piso zero, bônus por diferença de Elo, emblemas, limite de desafios, tag Mais desafiado e duplas. O pacote contém todas as correções anteriores. Não há publicação automática realizada pelo assistente.

## Validação

112 testes Python e 27 JavaScript passaram, com Google e consultas de rede simulados nos testes de integração. Foram verificados: IDs humanos e de jogadores sem Elo, as três modalidades de lista, exclusão de IA e histórico, saída da sala, confirmação expirada, falhas de conexão, consultas compartilhadas entre conexões SQLite, reabertura de perfis, atualização sem recarregar e preservação dos resultados e imagens anteriores.

A estrutura foi conferida em HTML público obtido das três listas em 13/09/2026. Durante a conferência final, novas requisições ao AoMStats esgotaram o tempo; isso não foi apresentado como uma detecção ao vivo bem-sucedida. O comportamento de expiração e recuperação foi validado com respostas controladas. A inspeção visual em Chromium não foi concluída porque o navegador não pôde ser baixado neste ambiente; a estrutura das páginas e o comportamento JavaScript foram testados localmente.
