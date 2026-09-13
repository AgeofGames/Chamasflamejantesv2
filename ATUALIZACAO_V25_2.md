# V25.2 — derrota de 30 pontos, tag e dupla no perfil

## Pontuação

A vitória padrão continua valendo **+30** e a derrota padrão passa a **−30**, em X1, duplas e trios. O valor novo vale para resultados confirmados após esta atualização. Os extratos e pontos já registrados na V25.1 permanecem como estavam.

| Situação | Vencedor | Derrotado |
| --- | ---: | ---: |
| Diferença de Elo de até 100 | +30 | −30 |
| Menor Elo vence com diferença maior que 100 e menor que 200 | +90 | −90 |
| Menor Elo vence com diferença de 200 a menos de 300 | +120 | −120 |
| Menor Elo vence com diferença de 300 a menos de 400 | +150 | −150 |
| Cada faixa adicional de 100, quando o menor Elo vence | Mais 30 | Menos 30 |
| Maior Elo vence, ou falta Elo conhecido para o bônus | +30 | −30 |

O piso continua sendo **zero, sem dívida**. Se o jogador tiver 1 vitória e 7 derrotas, estiver em zero e ganhar uma partida normal, passa a ter **30 pontos**, com 2 vitórias e 7 derrotas no histórico. Com as novas regras, seis vitórias seguidas e quatro derrotas seguintes, sem bônus, resultam em 60 pontos. A ordem das partidas e o piso zero continuam determinantes.

Permanecem os bônus por Elo registrado no desafio, o limite conjunto de três desafios por adversário por dia de Brasília, o bloqueio entre Elo 1300 ou mais e Elo 1000 ou menos, o ranking mensal e as regras dos dez emblemas. Rebaixamento de emblema não desconta pontos extras do ranking.

## Tag “Mais desafiado”

- A tag aparece nos perfis completos, nas janelas flutuantes, nos jogadores da Arena e nos rankings atuais.
- Conta desafios **X1 recebidos no mês**, pelo calendário de Brasília. Desafios ativos, concluídos e recusados contam.
- Desafios enviados, cancelados e convites para formar duplas ou trios não entram nessa contagem. Não altera pontos nem emblemas.
- Todos os líderes empatados recebem a tag. Sem desafios no mês, ninguém a recebe.
- A contagem reinicia a cada mês; o histórico dos confrontos continua guardado. Perfis desativados não recebem a tag.

## Dupla e notificações

1. O capitão cria a dupla e envia o convite.
2. O parceiro aceita pela notificação ou pela página da equipe.
3. O convite respondido sai das notificações e a dupla formada aparece imediatamente ao abrir o perfil de qualquer um dos dois, inclusive na janela flutuante. Duplas já existentes aparecem automaticamente.
4. Quem convidou recebe um aviso de aceite. Ele permanece até essa pessoa abrir a equipe e lê-lo, ou usar “Marcar todas como lidas”. Abrir o próprio perfil, o perfil do parceiro ou a lista de notificações não marca esse aviso como lido.
5. Ler o aviso não desfaz a dupla. Qualquer integrante confirmado pode usar **Desfazer dupla** no próprio perfil, na Arena 2×2 ou na página da dupla.
6. Ao desfazer, a dupla sai dos dois perfis e da lista ativa. Os jogadores podem formar outra dupla. A página antiga e seus resultados continuam disponíveis como histórico.

Com um duelo ativo, o bloqueio de alteração da equipe permanece. O capitão pode cancelar um desafio ainda não aceito; duelos aceitos devem ser concluídos antes de desfazer a dupla. Visitantes e pessoas apenas convidadas não podem desfazê-la. O funcionamento de sair de um trio foi preservado.

As notificações continuam atualizando automaticamente a cada três segundos enquanto a página está visível e há conexão. Resultados de partidas encerradas saem das notificações e permanecem nos históricos.

## Atualização e dados existentes

Envie o conteúdo completo deste ZIP ao repositório conectado ao Railway, incluindo `app.py`, os módulos `arena_*.py`, `templates` e `static`. Preserve banco SQLite, volume, fotos e variáveis atuais. Após o deploy, `/health` deverá mostrar **25.2-duplas-tags**.

A migração `arena_v25_2_migrated` identifica os avisos de aceite antigos para aplicar a regra de leitura. Não refaz os pontos já registrados na V25.1. Atualizações diretas de versões mais antigas executam também as correções anteriores que ainda não tiverem sido aplicadas. Nenhum histórico de duelo, emblema conquistado ou foto é apagado por esta atualização.

O pacote contém o site completo. A publicação no servidor deve ser feita pelo usuário; este trabalho foi preparado e validado localmente.

## Verificação

**96 testes Python e 20 JavaScript passaram**, com Google e AoMStats simulados. A cobertura inclui pontuação base e bônus, piso zero, limite de desafios, contagem mensal e empates da tag, aceite de dupla, duração dos avisos, permissões, desfazer por qualquer integrante, formação de outra dupla, preservação do histórico e atualização de bancos anteriores.

Para repetir:

```bash
python -m unittest discover -s tests -v
node --test tests/*.test.cjs
```
