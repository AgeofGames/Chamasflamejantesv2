# V23 — Histórico público e compartilhamento

## Perfis e histórico

O resumo exibido ao clicar em um jogador mostra quatro números: partidas concluídas, vitórias, derrotas e fugas. Elo e aproveitamento também continuam disponíveis. Logo abaixo, o histórico mostra o adversário, o resultado ou a recusa, data e hora em UTC e o ID quando informado.

As consultas usam paginação: cinco registros por página na janela flutuante, doze na página do perfil e vinte no histórico geral. Os totais são calculados sobre os registros completos, e não apenas sobre a página atual. Os filtros e links têm navegação por URL; na janela flutuante, a troca acontece dentro dela. Ao abrir um adversário dentro da janela, fechar retorna o foco e a rolagem à página original.

Uma fuga é uma recusa registrada pelo jogador desafiado. Se o adversário recusou, isso aparece como fuga do adversário e não aumenta o contador de quem enviou o desafio. Desafios cancelados não são listados nem acessíveis por seus antigos links públicos.

## Visibilidade e controles

Os desafios pendentes, aceitos, com ID aguardando confirmação, recusados e concluídos podem ser consultados por qualquer visitante. A Arena exibe os doze desafios ativos mais recentes e oferece acesso ao histórico completo. O ID aparece na Arena, no histórico e no próprio duelo após ser informado.

O acesso público não muda as permissões de escrita. Aceitar ou recusar continua sendo ação exclusiva do desafiado; cancelar um desafio pendente continua restrito ao desafiante; informar ou verificar a partida continua restrito aos participantes. As verificações de sessão e CSRF permanecem ativas. Dados de conta como e-mail não são exibidos no histórico público.

As páginas públicas de desafios podem ser lidas por robôs de compartilhamento. Desafios ainda não concluídos usam `noindex,follow`; não ficam bloqueados no `robots.txt`, para permitir a leitura dos metadados. Não foi adicionado envio de notificações para todos nem publicação automática em redes sociais.

## Cards

O resultado usa os avatares e nomes do duelo confirmado. O vencedor recebe coroa, louros e moldura dourada. O derrotado recebe uma moldura interrompida e efeito gráfico de rachaduras. A indicação de vitória só aparece para resultados concluídos e confirmados. Partidas pendentes e recusadas usam seus estados próprios, sem inventar um vencedor.

As artes dos torneios mostram modalidade, formato, nome, descrição, data, inscritos e premiação do próprio evento. FFA, Food/Wood/Gold, 1×1, 2×2 e as três modalidades MD3 têm composições e cores distintas. Eventos privados não fornecem imagem pública, mesmo que a requisição esteja autenticada como administrador.

As imagens são renderizadas no servidor em JPEG de 1200 × 630, usando os retratos e a arte já presentes no site. Não é necessário instalar um serviço externo de geração de imagens. As fontes DejaVu e sua licença estão incluídas. Os PNGs antigos de perfis e duelos continuam disponíveis nos endereços compatíveis.

Se houver avatar salvo, ele é usado primeiro. Para os endereços de avatar externos permitidos, há limites de conexão e leitura; falhas usam a inicial do jogador. O cache de renderização em memória é limitado. As amostras das sete modalidades ficaram entre aproximadamente 98 e 120 KB; fotos e textos diferentes podem alterar o tamanho.

Os botões de WhatsApp e demais redes compartilham o endereço público com metadados Open Graph completos. A prévia tem o vencedor e o derrotado, ou a modalidade do torneio. Quando um ID é informado sem recarregar a página, o card e seus botões também são atualizados.

**Enviar imagem** usa a Web Share API nos aparelhos compatíveis. A imagem é preparada antes do clique para preservar a autorização do navegador; se ainda não estiver pronta, o botão pede um novo toque. Em aparelhos sem suporte, a imagem é baixada. **Baixar card** permanece disponível, assim como os botões de link. Preparar a imagem tem prazo de dez segundos, com recuperação do botão em caso de erro.

## Atualização e validação

Envie o conteúdo do pacote ao repositório, preservando o banco, o volume, os uploads e as variáveis de ambiente. Nenhuma migração destrutiva foi adicionada. Confirme a versão `23-arena-publica-cards` no `/health` depois que o Railway mostrar a implantação ativa.

Passaram 40 testes Python e 9 testes JavaScript. Foram testados o acesso como visitante, a rejeição de ações por terceiros, contagens, filtros e paginação, exclusão de cancelados, imagens e metadados das sete modalidades, cabeçalhos GET/HEAD e cache, downloads, alteração de versão das imagens, preparo do arquivo, cancelamento do compartilhamento, timeout e navegação entre perfis. Os fluxos anteriores de login, torneios, notificações e confirmação de partidas também passaram.

As consultas externas nos testes foram simuladas. As artes de exemplo usaram dados fictícios e retratos do jogo, e foram inspecionadas visualmente. Não houve publicação no GitHub/Railway nem envio real de mensagens ao WhatsApp pelo assistente. A plataforma de destino decide o cache e o formato final da prévia; o card baixado pode ser anexado diretamente quando necessário.

Referências: [Open Graph](https://ogp.me/), [Web Share API](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/share). A licença das fontes acompanha `static/fonts/LICENSE-DejaVu.txt`.
