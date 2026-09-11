/* Native details remain usable without JS; a match request always has a deadline. */
(() => {
  'use strict';
  const floating = document.getElementById('community-challenges');
  if (floating) {
    const trigger = floating.querySelector('summary');
    const close = (restore) => { floating.open = false; if (restore) trigger.focus(); };
    floating.querySelector('[data-community-close]').addEventListener('click', () => close(true));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && floating.open) { close(true); event.preventDefault(); }
    });
    document.addEventListener('click', event => {
      if (floating.open && !floating.contains(event.target)) close(false);
    });
  }
  const showForm = () => {
    if (location.hash !== '#formar-equipe') return;
    const form = document.getElementById('formar-equipe');
    if (form) form.open = true;
  };
  showForm();
  window.addEventListener('hashchange', showForm);
  document.querySelectorAll('a[href="#formar-equipe"]').forEach(link => link.addEventListener('click', () => {
    const form = document.getElementById('formar-equipe');
    if (form) form.open = true;
  }));
  document.querySelectorAll('[data-team-match]').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (form.dataset.busy === 'true') return;
      form.dataset.busy = 'true';
      const button = form.querySelector('button');
      const message = form.querySelector('[role="status"]');
      const payload = new FormData(form);
      const previous = button.textContent;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 20000);
      button.disabled = true;
      button.textContent = 'Consultando…';
      form.setAttribute('aria-busy', 'true');
      message.textContent = 'Verificando os integrantes e o resultado no AoMStats…';
      try {
        const response = await fetch(form.action, {
          method: 'POST', body: payload, credentials: 'same-origin',
          headers: {Accept: 'application/json'}, signal: controller.signal
        });
        if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json')) {
          throw new Error('Sua sessão pode ter expirado. Reabra a página e entre novamente para verificar.');
        }
        const result = await response.json();
        message.textContent = result.message;
        if (result.refresh) location.assign(result.url);
      } catch (error) {
        message.textContent = error.name === 'AbortError'
          ? 'A consulta atingiu o limite de tempo e terminou. Confira o duelo antes de tentar novamente.'
          : (error.message || 'Não foi possível consultar agora. Tente novamente.');
      } finally {
        clearTimeout(timer);
        button.disabled = false;
        button.textContent = previous;
        form.dataset.busy = 'false';
        form.removeAttribute('aria-busy');
      }
    });
  });
})();
