# Validação da versão 22

Os testes foram executados localmente com bancos SQLite temporários. Nenhum cadastro real foi alterado.

## Fluxos verificados

- 18 páginas públicas, navegação compartilhada e todas as 113 páginas de build orders.
- Login Google com retorno simulado, validação do estado de login e configuração de perfil.
- Cadastro em torneio usando apenas o perfil da conta conectada, com bloqueio de inscrição duplicada.
- Criação, aceite, recusa e cancelamento de desafios, incluindo permissões, proteção CSRF e remoção de notificações.
- Partida aguardando resultado, confirmação do vencedor e proteção contra duplicação do resultado e notificações.
- Feed privado de notificações, contador de mensagens não lidas e marcação como lidas.
- Edição de frase e foto sem consulta externa, processamento da foto e limite de resolução final.
- Envio de feedback e pedidos de mapa com identificação do jogador.
- Sitemap, robots.txt e metadados de compartilhamento do perfil.
- Cache por versão do arquivo, gzip, recusa de gzip, resposta 304 e requisição parcial de arquivo.

O conjunto contém 14 testes de integração. Google e AoMStats foram simulados nos testes de rede; a autenticação e a consulta reais dependem das credenciais e da disponibilidade dos serviços após o deploy. Não foi realizado teste visual em navegador nesta atualização.

## Medição local da Arena

Mesmo cenário nas duas versões: 200 jogadores e 600 duelos concluídos, quatro carregamentos e mediana dos três últimos. A consulta externa do criador foi substituída por um retorno local nas duas versões.

| Medida | V21.1 | V22 |
| --- | ---: | ---: |
| Consultas SQL por página da Arena | 607 | 5 |
| Tempo mediano de resposta local | 39,8 ms | 18,1 ms |

O HTML do Guia de Teclas ocupou aproximadamente 612 KB sem compressão e 159 KB com gzip. As medições não representam uma garantia de tempo de carregamento no Railway: rede, quantidade de jogadores, volume do banco e serviços externos influenciam o resultado.

## Repetir os testes

```bash
python -m unittest discover -s tests -v
```

As animações usam CSS e IntersectionObserver sem biblioteca adicional; a preferência do aparelho é respeitada conforme a [documentação de movimento reduzido do MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion).
