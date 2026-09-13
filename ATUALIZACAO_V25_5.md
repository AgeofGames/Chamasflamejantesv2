# V25.5 — todos os jogadores no ranking X1

O ranking já era calculado para todos os jogadores, mas a tela exibia somente os dez primeiros. Esse limite foi removido: a lista ao lado dos jogadores agora mostra todos os perfis ativos com AoMStats, inclusive quem ainda está com zero pontos e não disputou partidas.

A posição segue a ordenação existente: pontos, vitórias, derrotas e ID do jogador como último desempate. As fotos redondas, os emblemas depois do nome, a tag Mais desafiado e os indicadores de presença foram preservados. O mesmo componente dos rankings de duplas e trios também passa a exibir a lista inteira.

O botão no final agora se chama **Ver temporadas e regras**, pois o ranking completo já aparece na Arena.

## Atualizar o site

Envie o conteúdo completo do ZIP ao GitHub conectado ao Railway. Preserve banco, volume, fotos e variáveis. Depois do deploy, `/health` deverá indicar **25.5-ranking-completo**.

Não é necessário alterar ou reenviar resultados. Esta revisão muda a exibição; o cálculo de pontos, os históricos, as duplas e as notificações continuam com as regras anteriores. A integração de presença do AoMStats da V25.4 está incluída.

## Verificação

Conferência em banco local isolado com 30 jogadores elegíveis: os rankings X1, duplas e trios exibiram todos os 30, numerados de 1 a 30. Foram conferidos a ordem por pontuação, jogadores sem partidas, fotos, emblemas, links de perfil e marcadores de presença. Perfis inativos ou sem AoMStats continuaram excluídos, e os resultados registrados permaneceram idênticos após abrir as páginas. Não foram feitas consultas externas durante essa verificação.
