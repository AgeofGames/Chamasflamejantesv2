# Capa de compartilhamento — V22.1

Arquivo final: `static/share/chamas-flamejantes-v22-1.jpg`.

JPEG progressivo, 1200 × 630 pixels, 223.634 bytes. A imagem é servida pelo próprio Flask, sem autenticação, com URL absoluta e versão pelo conteúdo. Os metadados ficam no HTML inicial de `templates/base.html`, dentro do bloco substituível `social_meta`. Assim, os perfis e duelos preservam suas imagens específicas.

O teste `test_default_link_preview_is_public_and_complete` verifica a imagem padrão em cinco páginas, os metadados, o acesso anônimo, o formato e as dimensões reais, GET/HEAD, o limite de 300 KB e a preservação das prévias dos perfis e desafios. A apresentação efetiva no WhatsApp só pode ser conferida após publicar a atualização. O aplicativo controla seu cache e a forma de exibir o cartão.

Fonte técnica: [Open Graph — propriedades de imagem](https://ogp.me/#structured).

## Criação da arte

Arte produzida com a ferramenta integrada de geração de imagens. Referências: os retratos de Zeus e Rá já presentes em `static/knowledge/gods/zeus.webp` e `static/knowledge/gods/ra.webp`. A exportação para o site ajusta o tamanho e a compressão, mantendo a composição aprovada.

Prompt utilizado:

> Use case: ads-marketing. Create one FINAL finished horizontal website social-sharing cover for the Brazilian Age of Mythology: Retold community site CHAMAS FLAMEJANTES. Output a landscape image with exact 1200 x 630 pixel dimensions (1.905:1 aspect ratio), ideal for a WhatsApp link preview, preferably JPEG. The two supplied pictures are reference artwork of Zeus and Ra from the site's existing game cards; preserve their recognizable appearance. This is an original promotional composition, not a screenshot or UI mockup. Professional premium strategy-game campaign design, crisp recognizable Zeus portrait on left and Ra on right, expertly composited around a central clean dark obsidian field. Faces clearly lit and visible, warm golden rim light and subtle blue lightning by Zeus, sculptural Egyptian gold by Ra. Main palette charcoal, warm orange flames, bronze, ivory; restrained realistic ember particles, no excessive glow, no neon-purple aesthetic, no generic messy AI fantasy collage. Hierarchy must remain readable in a tiny WhatsApp preview: small elegant flame emblem above very large, beautifully typeset central two-line title EXACTLY 'CHAMAS' then 'FLAMEJANTES' in strong ivory/brushed golden serif letters. Title occupies most central space, do not let portraits overlap text. Directly below, medium clear sans-serif line EXACTLY 'AGE OF MYTHOLOGY: RETOLD'. Lower strip, with spacious clean spacing, feature text EXACTLY '113 BUILD ORDERS' and 'TORNEIOS • ARENA X1'; make 113 an orange accent with strong emphasis. Along bottom small but legible site address EXACTLY 'chamasflamejantes.com.br'. Title and meaningful features within an inner 8% safe margin. Cinematic but professionally restrained, bright detailed game faces, excellent contrast and balanced composition. No invented endorsements, no Microsoft logo, no 'official game' claims, no extra text, no watermark, no tiny decorative paragraphs.
