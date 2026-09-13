/* Public AoMStats activity. All avatars share one request and expire locally. */
(() => {
  const labels = {lobby: 'Em sala no Age · detectado pelo AoMStats',
    match: 'Em partida no Age · detectado pelo AoMStats'};
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
      if ((node.dataset.aomState || '') === (item ? item.state : '')) return;
      if (item) {
        node.dataset.aomState = item.state;
        node.setAttribute('title', labels[item.state]);
        node.setAttribute('aria-label', [original.aria, labels[item.state]].filter(Boolean).join(' · '));
      } else {
        delete node.dataset.aomState;
        for (const [key, value] of [['title', original.title], ['aria-label', original.aria]]) {
          if (value === null) node.removeAttribute(key); else node.setAttribute(key, value);
        }
      }
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
        if (expires > Date.now()) fresh.set(id, {state: item.state, expires});
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
