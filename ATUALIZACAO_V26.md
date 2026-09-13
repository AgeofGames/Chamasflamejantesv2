# V26 — Comunidade, jornada do jogador e ID da partida detectada

Esta atualização reúne os oito recursos pedidos e acrescenta a identificação da partida à presença do AoMStats. Mantém o banco existente, resultados, fotos, duplas, torneios, mapas, build orders e as dez artes dos emblemas.

## Onde encontrar

| Recurso | Acesso e comportamento |
| --- | --- |
| Presença e ID | Fotos continuam com a luz verde quando o AoMStats confirma sala ou partida. Perfis, janela flutuante, cards de jogadores, rankings e integrantes da equipe exibem **Partida + ID + Copiar ID** quando a fonte fornece uma partida em andamento. |
| Rivalidades | Perfil → Jornada → Rivalidades, ou **Ver rivalidade** no duelo concluído. Placar X1, adversários, última vitória de cada lado, maior sequência e histórico paginado. |
| Evolução | Perfil → Jornada → Evolução. Selecione mês e modalidade; clique ou use o teclado nos pontos do gráfico para consultar resultado, bônus por Elo e saldo. Há também uma tabela de todas as partidas do período. |
| Mural | **Mural** no menu. Publique estratégia ou novidade; depois de vencer, use **Publicar minha vitória no mural** no duelo. Publicações têm comentários e curtidas. |
| Agendamento | Abra um desafio aceito → Horário do duelo. Um jogador ou capitão propõe, o adversário aceita ou sugere outro horário. A lista pessoal fica em **Minha agenda**. |
| Conquistas | Perfil → Jornada → Conquistas. Primeira vitória; **Chama imparável** por cinco vitórias seguidas na mesma modalidade; **Caçador de gigantes** por vencer um adversário de Elo maior. |
| Capas | Próprio perfil → **Escolher capa**. Selecione Chamas Flamejantes ou uma das artes disponíveis de deuses e panteões. A capa aparece também na janela flutuante. |
| Build orders | Abra uma build → Minhas anotações. Marque favorita e escreva suas observações. A coleção está em **Minhas build orders**. |
| Replays | Duelo concluído → Replays e análise → Anexar meu replay. Visitantes podem baixar; jogadores com perfil vinculado podem comentar. |

## Presença e botão de copiar

- O jogador é associado pelo identificador do AoMStats, sem inferir presença pelo nome, login Google ou histórico de partidas antigas.
- Uma sala aberta aparece como **Em sala**. Seu número não é mostrado como ID de partida.
- Uma partida atual com ID válido mostra o número e o botão. A cópia leva somente os dígitos para a área de transferência. Se o navegador bloquear a cópia, o número permanece selecionável para copiar manualmente.
- Entrar em outra partida atualiza o número automaticamente. Presença e ID expiram juntos, inclusive quando a conexão falha. “Presença não confirmada” não significa necessariamente que a pessoa está offline.
- Os avatares compartilham a mesma consulta. O navegador consulta a cada 20 segundos; o servidor reaproveita as fontes por 45 segundos. A confirmação local dura no máximo 90 segundos e respeita a idade da informação do AoMStats. A detecção depende da atualização pública do provedor.
- Copiar o ID não registra automaticamente o resultado na Arena. A confirmação do vencedor continua usando o fluxo de verificação do duelo.

## Histórico, pontos e conquistas

A evolução lê o extrato já registrado na Arena. Não altera pontos nem calcula o ranking multiplicando totais de vitórias e derrotas. O gráfico distingue o valor da regra e a variação realmente aplicada quando o saldo já estava em zero.

A base permanece **+30 / −30**, com os bônus por diferença de Elo. O saldo não fica negativo: depois de várias derrotas em zero, uma vitória normal dá 30 pontos. As restrições de Elo, três desafios por adversário ao dia, regras de rebaixamento, ranking mensal, tag “Mais desafiado” e ranking completo permanecem.

As rivalidades incluem duelos X1 concluídos de todas as temporadas. Recusas e cancelamentos não são vitórias ou derrotas no placar. O histórico anterior de fugas continua no perfil.

As conquistas são permanentes e usam o histórico salvo, inclusive temporadas encerradas. Primeira vitória e sequência podem reconhecer resultados antigos. A conquista por Elo exige os valores registrados no confronto; não usa o Elo atual para inventar um bônus ou conquista retroativa.

## Agendamentos e lembretes

- Horários são apresentados no fuso de Brasília, com antecedência entre cinco minutos e 90 dias.
- O desafio deve estar aceito e ainda sem ID informado. Apenas os dois jogadores do X1 ou os capitães podem propor, responder ou cancelar o horário.
- Trocar o horário exige novo aceite. Respostas a versões antigas são recusadas. Cancelar o agendamento mantém o desafio ativo.
- Todos os participantes recebem um lembrete na janela dos 15 minutos anteriores e outro no horário marcado. Cada etapa é registrada uma vez por participante e versão do agendamento, inclusive com vários workers do servidor.
- Um processo leve verifica a agenda a cada 20 segundos enquanto o serviço está ativo. A consulta de notificações também processa lembretes pendentes. Ao reiniciar dentro dos 15 minutos posteriores ao horário, o lembrete de início pode ser recuperado. Indisponibilidade prolongada do serviço pode impedir um lembrete.
- São notificações dentro do site. Não é necessário atualizar a página; continuam consultadas a cada três segundos. Não há envio por e-mail, WhatsApp ou push com o navegador fechado.
- Avisos de horário lidos desaparecem das notificações. Duelo concluído deixa de exibir esses avisos, preservando horário e resultado no histórico. O ciclo anterior dos convites de dupla permanece.

## Mural, notas e replays

Publicações de vitória exigem um resultado confirmado e um autor pertencente ao lado vencedor. O card usa as imagens já existentes de resultado. Reenviar a mesma publicação ou curtida não duplica o registro. O autor pode editar ou remover sua publicação; administradores podem moderar. Cada pessoa controla seus próprios comentários. Comentários em uma publicação ou replay geram aviso ao autor, que desaparece ao ler a página.

Favoritos e anotações são privados por conta Google. Uma anotação pode ser guardada sem marcar a build como favorita. São aceitos até 6.000 caracteres por build.

Cada participante pode anexar um replay `.mythrec` de até 32 MiB por duelo concluído, com versão do jogo e descrição opcionais. Arquivos iguais não se duplicam no mesmo duelo. O envio é identificado pelo autor; o site não reproduz nem interpreta o replay e não usa o arquivo para confirmar ou alterar o vencedor. O resultado continua validado pelo AoMStats. Para assistir, é necessário abrir o replay no jogo, com uma versão compatível.

O download é público, como anexo. Os arquivos ficam fora da pasta de fotos e recebem nomes internos aleatórios. Remover uma publicação ou replay não remove a partida nem seus pontos. Autor e administrador podem remover o replay da página.

## Atualização no Railway

1. Extraia o ZIP e envie seu conteúdo completo ao repositório já conectado ao Railway. Os arquivos `app.py`, `community_hub.py`, `duel_extras.py`, templates e pasta `static` precisam estar juntos.
2. Preserve o volume persistente, o banco SQLite, as fotos e as variáveis atuais. Não crie um banco vazio em substituição ao existente.
3. As tabelas novas são criadas automaticamente. Os replays ficam em `arena_replays`, ao lado do arquivo indicado em `DATABASE_PATH`. Essa pasta precisa permanecer no mesmo volume persistente do banco.
4. Após a implantação ativa, confira `/health`: `version` deve ser `26-comunidade-jornada`.
5. Abra um perfil, o Mural e um duelo aceito para conferir as novas opções. A presença exige dados atuais do AoMStats para mostrar a luz e o ID.

Não há novas credenciais obrigatórias. `ARENA_REMINDERS_ENABLED=0` desativa apenas o processo periódico de lembretes; a consulta autenticada das notificações ainda processa lembretes devidos. O limite global configurável `MAX_UPLOAD_MB` continua valendo para todo o site; se estiver abaixo de 33 MB, também limita uploads de replay antes do limite específico de 32 MiB.

## Validação do pacote

**137 testes Python e 40 JavaScript passaram**, incluindo as funções anteriores e a integração dos novos recursos: isolamento das contas, CSRF, permissões, migração repetida, histórico, pontos congelados por Elo, piso zero, paginação, moderadores, curtidas idempotentes, lembretes sem duplicação, versões dos horários, elencos das equipes, upload/download/remoção de replays, ranking completo e presença com cópia/expiração do ID.

Google e AoMStats foram simulados nos testes. As páginas foram renderizadas localmente e os comportamentos de JavaScript foram exercitados com DOM de teste. Não foi possível executar a inspeção visual em Chromium neste ambiente. Este pacote não foi implantado pelo assistente no site publicado.
