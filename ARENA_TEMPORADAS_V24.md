> Documento histórico da V24. As regras de pontuação, limites e atualização vigentes estão em ATUALIZACAO_V25.md.

# Arena V24: equipes e temporadas

## Atualização

Este pacote é o site completo. Substitua os arquivos do repositório pelo conteúdo do ZIP, incluindo as novas pastas e módulos. Preserve o banco SQLite, o volume, as fotos enviadas e todas as variáveis já configuradas no Railway. Não apague a pasta de dados do servidor.

As tabelas novas são criadas automaticamente na inicialização. A migração importa uma única vez os duelos X1 que possuem resultado confirmado pelo AoMStats e data de conclusão, em ordem de confirmação. Os registros antigos ficam preservados; duelos antigos sem confirmação verificável continuam no histórico, mas não recebem pontos inventados.

Depois que a implantação terminar, o campo version em /health deve ser 24-equipes-temporadas. O pacote foi preparado e validado localmente; não foi publicado no GitHub/Railway pelo assistente.

## Janela da comunidade

A Arena X1 mantém jogadores e classificação lado a lado no computador. Os desafios deixam de ocupar uma seção grande antes dos jogadores. Um botão fixo abre uma janela de até 390 pixels, com lista rolável, avatares pequenos, estado e ID informado. A janela inicia fechada e pode ser fechada por botão, Escape ou clique fora. Há acesso ao histórico completo. No celular, as colunas se reorganizam para caber na tela.

## Duplas e trios

Abra Arena e escolha Duplas (2×2) ou Trios (3×3). Cada jogador pode integrar uma equipe de cada modalidade.

1. O capitão informa o nome da equipe e escolhe um ou dois parceiros já cadastrados com AoMStats.
2. Cada parceiro recebe um convite na janela de notificações e precisa aceitar. Recusar um convite de formação não conta como derrota ou fuga de um duelo.
3. Com os integrantes confirmados, o capitão abre o perfil de outra equipe da mesma modalidade e envia o desafio.
4. O capitão desafiado aceita ou recusa. Todos os integrantes são avisados pelo chat de notificações.
5. Quando todos terminarem a partida, qualquer integrante dos dois elencos pode informar o ID do AoMStats.
6. O site confere os quatro ou seis perfis exatos e os indicadores de vitória e derrota de cada jogador. Os vencedores precisam corresponder a uma equipe inteira. Jogadores extras, perfis errados, resultados incompletos ou dessincronizados não confirmam uma vitória.

Cada equipe tem no máximo um desafio ativo. O elenco do duelo é guardado no envio e não pode ser alterado enquanto o desafio estiver ativo. O capitão desafiante pode cancelar enquanto ninguém aceitou; o desafio e seu link deixam de funcionar. IDs de duelos cancelados não são reutilizados. Uma equipe sem duelo ativo permite a saída de integrantes; o capitão pode encerrá-la e os resultados antigos continuam disponíveis.

Se um convite for recusado ou um integrante sair, o capitão pode convidar outro para preencher a vaga. Equipes precisam estar completas e disponíveis para um novo desafio. Remover uma conta pelo painel encerra seus vínculos de equipe e cancela seus desafios ativos, preservando os resultados antigos.

As consultas verificam a página da partida e o histórico de Customs/Quickplay de um integrante de cada elenco. Há limite de tempo, sem repetição automática infinita. Um ID ainda não encontrado fica salvo para uma verificação manual ou correção. Uma partida já registrada não pode ser reutilizada em outro duelo, inclusive entre X1 e equipes.

## Pontos e emblemas

Os rankings são individuais e separados por X1, 2×2 e 3×3. Em equipe, todos os integrantes recebem a vitória ou a derrota confirmada.

| Nível | Emblema | Pontos |
| --- | --- | --- |
| 1 | Brasa | 0–99 |
| 2 | Chama | 100–199 |
| 3 | Forja | 200–299 |
| 4 | Guardião | 300–399 |
| 5 | Guerreiro | 400–499 |
| 6 | Conquistador | 500–599 |
| 7 | Herói | 600–699 |
| 8 | Lenda | 700–799 |
| 9 | Titã | 800–899 |
| 10 | Imortal | 900–999 |

- Vitória: +30 pontos; derrota: −15. Mínimo zero, máximo 999.
- Três derrotas consecutivas OU quatro acumuladas desde o último gatilho causam um rebaixamento. Vitórias interrompem a sequência, mas não apagam o contador acumulado.
- O rebaixamento limita a pontuação ao teto do nível abaixo daquele que o jogador tinha antes da derrota. Se os −15 pontos já causarem a queda de nível nessa partida, a punição não derruba outro nível.
- Os dois gatilhos nunca se somam na mesma partida. Depois de um gatilho, os contadores de sequência e derrotas acumuladas reiniciam.
- Recusas e cancelamentos não alteram pontos. Não são derrotas em partidas.
- Desempate: pontos, mais vitórias, menos derrotas e ordem de cadastro.

Exemplo: com 180 pontos, três derrotas seguidas resultam em 165, 150 e 99. Com 240 pontos, três derrotas resultam em 225, 210 e 195: a última derrota já diminuiu um nível e não há segunda queda.

## Virada mensal

O calendário usa America/Sao_Paulo, horário de Brasília. À meia-noite do primeiro dia do mês, o ranking passa a consultar a nova temporada, começando em zero. O histórico não é apagado. Vale a data em que o site confirmou o resultado, não a data do convite.

Quem disputou pelo menos uma partida ganha o emblema do nível em que encerrou cada modalidade. O emblema final, pontos e posição são guardados no perfil. Os níveis atuais podem cair com derrotas; as conquistas de meses anteriores ficam preservadas.

Não é preciso configurar cron. A nova classificação é determinada pela data atual; o encerramento e os prêmios antigos são gravados de forma idempotente no primeiro acesso ao ranking ou perfil, mesmo se o servidor ficou desligado na virada.

## Histórico e compartilhamento

O perfil exibe os emblemas atuais, pontos, derrotas consecutivas/acumuladas e as conquistas anteriores. Um acesso separado mostra os duelos em equipes, com adversários, elencos, IDs e resultados públicos.

Duplas e trios têm cards próprios em JPEG 1200×630, com os avatares de todos os integrantes. Uma vitória confirmada destaca os vencedores com coroas e os derrotados com efeito gráfico de rachaduras. O link inclui os metadados da imagem no HTML. Há botões de WhatsApp, outras redes, envio da imagem em aparelhos compatíveis e download.

## Validação

66 testes Python e 14 testes JavaScript passaram. Cobrem convites, permissões dos capitães e integrantes, CSRF, recusa, cancelamento, elencos exatos, confirmação de duplas e trios, reuso de IDs, atualização concorrente, pontuação única, limites e gatilhos de queda, virada do mês, migração e preservação de registros.

Também foram verificados HTML público e imagens dos novos duelos, perfis, notificações, a janela compacta, fechamento por teclado e a recuperação do carregamento após erro ou timeout. Os testes anteriores de login Google, X1, busca, torneios, compartilhamento, favicon e sitemap continuam passando.

As consultas externas foram simuladas nos testes. Os cards e um emblema foram renderizados e inspecionados; as amostras usam dados fictícios. Não houve partida real de equipe nem envio de mensagem pelo WhatsApp. O aplicativo de destino controla o formato e o cache final da prévia.
