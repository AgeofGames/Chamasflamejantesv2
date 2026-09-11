/* One bounded lookup per explicit click. No timers that poll the match. */
(() => {
  'use strict';
  let busy = false;
  const feedback = (panel, message, error = false) => {
    const target = panel?.querySelector('[data-match-feedback]');
    if (target) { target.textContent = message; target.classList.toggle('error', error); }
  };
  const sameOrigin = value => {
    const url = new URL(value, window.location.href);
    return url.origin === window.location.origin ? url.href : null;
  };
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (!form.matches('form[data-match-lookup]') || !window.fetch || !window.AbortController) return;
    // The shared form guard runs first. Clear its markers when this request ends.
    event.preventDefault();
    if (busy) return;
    const panel = form.closest('#duel-match-panel');
    if (!panel) return;
    busy = true;
    const body = new FormData(form);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    const buttons = [...panel.querySelectorAll('button')];
    const submitter = event.submitter || form.querySelector('button');
    buttons.forEach(button => { button.disabled = true; });
    submitter?.setAttribute('aria-busy', 'true');
    panel.setAttribute('aria-busy', 'true');
    feedback(panel, 'Consultando partidas ranqueadas e Customs/Quickplay…');
    try {
      const response = await fetch(form.action, {
        method:'POST', body, credentials:'same-origin', signal:controller.signal,
        headers:{'Accept':'application/json'}, cache:'no-store',
      });
      if (!response.headers.get('Content-Type')?.includes('application/json')) {
        throw new Error('A sessão expirou ou o servidor não respondeu. Recarregue esta página para conferir o duelo e tentar novamente.');
      }
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || 'Não foi possível consultar. Recarregue a página e tente novamente.');
      if (data.state === 'completed' && data.redirect) {
        const target = sameOrigin(data.redirect);
        if (target) { feedback(panel, data.message); window.location.assign(target); return; }
      }
      if (data.html) {
        panel.outerHTML = data.html;
        document.getElementById('duel-match-panel')?.focus({preventScroll:true});
      } else feedback(panel, data.message || 'Consulta encerrada.', data.state === 'invalid');
      if (data.chat_html) {
        const chat = document.querySelector('.duel-chat-thread');
        if (chat) chat.innerHTML = data.chat_html;
      }
      if (data.share_html) {
        const card = document.querySelector('.share-card-panel');
        if (card) {
          card.outerHTML = data.share_html;
          document.dispatchEvent(new CustomEvent('chamas:content', {detail:{container:document.querySelector('.share-card-panel')}}));
        }
      }
      document.querySelectorAll('[data-duel-state-label]').forEach(label => { label.textContent = data.label; });
      const description = document.querySelector('[data-duel-state-description]');
      if (description && data.status === 'match_pending') description.textContent = 'ID guardado. A consulta terminou sem confirmar o resultado; você pode verificar novamente ou corrigir o ID abaixo.';
      const link = document.querySelector('[data-duel-match-link]');
      if (link && data.match_id && data.match_url) {
        const url = new URL(data.match_url);
        if (url.protocol === 'https:' && url.hostname === 'aomstats.io') {
          link.href = url.href; link.textContent = `PARTIDA #${data.match_id} ↗`; link.hidden = false;
        }
      }
    } catch (error) {
      feedback(panel, error.name === 'AbortError'
        ? 'A consulta foi interrompida pelo limite de tempo. Não há busca contínua nesta tela. Recarregue para conferir se o resultado foi registrado ou tente novamente.'
        : (error.message || 'Falha de conexão. Tente novamente em alguns instantes.'), true);
    } finally {
      window.clearTimeout(timeout);
      busy = false;
      panel.removeAttribute('aria-busy');
      buttons.forEach(button => { button.disabled = false; button.removeAttribute('aria-busy'); button.removeAttribute('aria-disabled'); });
      panel.querySelectorAll('form[data-submitting]').forEach(item => { delete item.dataset.submitting; item.removeAttribute('aria-busy'); });
    }
  });
})();
