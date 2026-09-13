/* Public AoMStats activity. All avatars share one request and expire locally. */
(() => {
  const labels = {lobby: 'Em sala no Age · detectado pelo AoMStats',
    match: 'Em partida no Age · detectado pelo AoMStats'};
  const validId = value => /^[1-9]\d{0,19}$/.test(value || '');
  const unknown = 'Presença no Age não confirmada';
  const originals = new WeakMap();
  let players = new Map(), nextCheck = 0, inFlight = null, failures = 0;

  function render() {
    const now = Date.now();
    for (const [id, item] of players) if (item.expires <= now) players.delete(id);
    document.querySelectorAll('[data-aom-player]').forEach(node => {
      const item = players.get(node.dataset.aomPlayer);
      if (!originals.has(node)) originals.set(node, {
        title: node.getAttribute('title'), aria: node.getAttribute('aria-label')});
      const original = originals.get(node);
      if ((node.dataset.aomState || '') === (item ? item.state : '') && (node.dataset.aomMatchId || '') === (item?.matchId || '')) return;
      if (item) {
        node.dataset.aomState = item.state;
        node.dataset.aomMatchId = item.matchId || '';
        node.setAttribute('title', labels[item.state] + (item.matchId ? ' · Partida #' + item.matchId : ''));
        node.setAttribute('aria-label', [original.aria, labels[item.state]].filter(Boolean).join(' · '));
      } else {
        delete node.dataset.aomState;
        delete node.dataset.aomMatchId;
        for (const [key, value] of [['title', original.title], ['aria-label', original.aria]]) {
          if (value === null) node.removeAttribute(key); else node.setAttribute(key, value);
        }
      }
    });
    document.querySelectorAll('[data-aom-match]').forEach(node => {
      const item = players.get(node.dataset.aomMatch);
      const matchId = item?.state === 'match' && validId(item.matchId) ? item.matchId : '';
      node.hidden = !matchId;
      const value = node.querySelector('[data-aom-match-value]');
      const copy = node.querySelector('[data-copy-match]');
      if (!value || !copy) return;
      if (copy.dataset.copyMatch !== matchId) {
        value.textContent = matchId;
        copy.dataset.copyMatch = matchId;
        copy.textContent = 'Copiar ID';
        const note = node.querySelector('[data-aom-copy-status]');
        if (note) note.textContent = '';
      }
      copy.disabled = !matchId;
    });
    document.querySelectorAll('[data-aom-status]').forEach(node => {
      const item = players.get(node.dataset.aomStatus);
      const label = item ? labels[item.state] : unknown;
      if (node.textContent !== label) node.textContent = label;
      const state = item ? item.state : 'unknown';
      if (node.dataset.aomState !== state) node.dataset.aomState = state;
    });
  }

  async function refresh(force = false) {
    render();
    if (document.hidden || inFlight || (!force && Date.now() < nextCheck) ||
        !document.querySelector('[data-aom-player]:not([data-aom-player=""])')) return;
    const controller = new AbortController();
    inFlight = controller;
    const started = Date.now();
    const timeout = setTimeout(() => controller.abort(), 16000);
    try {
      const response = await fetch('/api/arena/presenca', {
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
        headers: {'Accept': 'application/json'}});
      if (!response.ok) throw new Error('Presence temporarily unavailable');
      const data = await response.json();
      if (!data || !data.players || typeof data.players !== 'object' || Array.isArray(data.players))
        throw new Error('Invalid presence response');
      const fresh = new Map();
      for (const [id, item] of Object.entries(data.players)) {
        if (!/^\d+$/.test(id) || !item || !Object.hasOwn(labels, item.state) ||
            typeof item.expires_in !== 'number' || !Number.isFinite(item.expires_in)) continue;
        // Start from request time: slow responses cannot extend a green light.
        const expires = started + Math.min(90, Math.max(0, item.expires_in)) * 1000;
        if (expires > Date.now()) fresh.set(id, {state: item.state, expires, matchId: item.state === 'match' && typeof item.match_id === 'string' && validId(item.match_id) ? item.match_id : ''});
      }
      players = fresh;
      failures = 0;
      nextCheck = Date.now() + 20000;
      render();
    } catch (_) {
      failures = Math.min(failures + 1, 3);
      nextCheck = Date.now() + Math.min(60000, 10000 * 2 ** failures);
      render();
    } finally {
      clearTimeout(timeout);
      inFlight = null;
    }
  }

  document.addEventListener('click', async event => {
    const button = event.target.closest?.('[data-copy-match]');
    if (!button) return;
    event.preventDefault(); event.stopPropagation();
    const wrapper = button.closest('[data-aom-match]');
    const item = wrapper && players.get(wrapper.dataset.aomMatch);
    if (!item || item.state !== 'match' || item.expires <= Date.now() || !validId(item.matchId)) { render(); return; }
    const matchId = item.matchId;
    const note = wrapper.querySelector('[data-aom-copy-status]');
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(matchId);
      if (button.dataset.copyMatch === matchId && !wrapper.hidden) {
        button.textContent = 'ID copiado ✓';
        if (note) note.textContent = 'ID ' + matchId + ' copiado.';
      }
    } catch (_) {
      // Keep a selectable ID even if clipboard permission is unavailable.
      const value = wrapper.querySelector('[data-aom-match-value]');
      const selection = window.getSelection?.();
      if (selection && value) { const range = document.createRange(); range.selectNodeContents(value); selection.removeAllRanges(); selection.addRange(range); }
      if (note && !wrapper.hidden) note.textContent = 'Selecione o ID e copie manualmente.';
    }
  });

  // Expiration keeps running even when a request fails or connectivity drops.
  setInterval(() => refresh(), 1000);
  document.addEventListener('chamas:content', () => refresh());
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { if (inFlight) inFlight.abort(); render(); }
    else refresh(true);
  });
  window.addEventListener('focus', () => refresh(true));
  window.addEventListener('online', () => refresh(true));
  window.addEventListener('pageshow', () => refresh(true));
  refresh();
})();
