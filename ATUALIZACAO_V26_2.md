# V26.2 — Ordem do perfil

## Organização

A coluna de conteúdo do perfil agora segue esta ordem:

1. **Histórico público** — Números na Arena e botão para ver com quem jogou.
2. **Compartilhar perfil**.
3. **Temporada — Emblemas da Arena**.
4. **Dupla · 2×2**, quando o jogador tem uma dupla formada.
5. **Evolução dos pontos**.
6. **Rivalidades**.
7. **Conquistas**.

O mês da temporada continua automático: por exemplo, setembro de 2026 aparece como **09/2026**. A virada do mês e os emblemas anteriores mantêm o comportamento existente.

No próprio perfil, os quatro controles ficam em um card pequeno imediatamente abaixo do card de identidade da Arena: **Alterar meus dados**, **Abrir notificações**, **Escolher capa** e **Minha agenda**. O título **Este perfil é seu** e seu parágrafo foram retirados. Os botões mantêm as ações e endereços existentes.

No computador, esse card fica na coluna da identidade. No celular, acompanha o perfil na mesma coluna. Os emblemas aparecem uma única vez na página; a janela flutuante continua exibindo os emblemas e a dupla. Os controles de desafio de outros perfis continuam disponíveis abaixo da identidade.

## Dados e recursos preservados

Esta revisão altera a disposição dos cards e a apresentação dos controles. Não introduz migração nem recálculo de pontos. Histórico completo, pontos e bônus, temporadas, conquistas, duplas, fotos e capas, notificações, presença e cópia de ID, agendamentos, replays e compartilhamento são preservados. Mural e coleção de favoritas/anotações permanecem removidos conforme a V26.1.

## Atualizar

1. Extraia o ZIP e envie o conteúdo completo ao GitHub conectado ao Railway, incluindo módulos, templates e `static`.
2. Preserve o banco, volume, fotos, replays e variáveis do serviço. Não é necessária nova configuração.
3. Aguarde a implantação ativa. `/health` deverá informar **26.2-ordem-perfil**.
4. Abra o próprio perfil para conferir os botões abaixo da identidade e os sete blocos na ordem acima.

## Validação desta revisão

- 20 testes Python existentes passaram com banco isolado e integrações externas simuladas.
- Conferência em Chromium nas larguras de 1920, 1024, 768 e 390 pixels.
- Verificadas a ordem dos sete blocos, a posição e largura do card de quatro botões, a ausência do título antigo e a ausência de emblemas duplicados.
- Gráfico, expansão das seções, janela de perfil e controles de desafio conferidos, sem erros de JavaScript ou rolagem horizontal.

O pacote está preparado para publicação no GitHub/Railway pelo responsável pelo site.
