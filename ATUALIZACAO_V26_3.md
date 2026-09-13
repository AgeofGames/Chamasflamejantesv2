# V26.3 — Histórico proporcional ao perfil

O card **Com quem jogou** foi colocado dentro da coluna dos demais cards do perfil, imediatamente abaixo de **Conquistas**. Ele tem a mesma largura e alinhamento do card acima, com o mesmo espaçamento entre os blocos.

As linhas das partidas têm disposição compacta, com os dados do adversário, resultado, ID e pontos, seguidos de data e link do duelo. Em telas menores, as informações se organizam em uma coluna.

Os seis filtros, a paginação e o botão **Ver com quem jogou** mantêm o comportamento existente. Nenhum registro é removido. O histórico na janela flutuante do perfil também continua disponível.

## Atualizar

Extraia o ZIP e envie seu conteúdo completo ao repositório conectado ao Railway, incluindo `templates` e `static`. Preserve banco, volume, fotos, replays e variáveis atuais. Após a implantação, `/health` deverá informar **26.3-historico-compacto**.

Esta revisão é visual, sem nova migração ou recálculo de pontos. A ordem dos demais cards e os quatro botões abaixo da identidade do perfil permanecem como na V26.2.

## Validação

- 5 testes Python existentes de perfis, filtros e paginação do histórico passaram com dados isolados e integrações externas simuladas.
- Conferência em Chromium nas larguras de 1920, 1024, 768 e 390 pixels: largura e alinhamento iguais aos de Conquistas, sem rolagem horizontal.
- Filtros de vitórias e derrotas conferidos na interface.
- Pacote completo validado por extração e comparação dos arquivos, incluindo a cópia final disponibilizada para download.
