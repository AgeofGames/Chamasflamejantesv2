(() => {
  'use strict';
  const modal = document.getElementById('profile-modal');
  const content = document.getElementById('profile-modal-content');
  const notifications = document.getElementById('notification-popover');
  const toggle = document.querySelector('[data-notification-toggle]');
  let opener, retryTrigger, controller, requestNumber = 0, previousOverflow = '';
  let feedCursor = '', feedBusy = false, feedEnabled = !!notifications, lastFeed = 0;
  let feedDelay = 3000, feedAbort;
  let knownUnread = Number(toggle?.querySelector('b')?.textContent) || 0;
  const focusable = container => [...container.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]):not([type=hidden]),textarea:not([disabled]),select:not([disabled]),[tabindex="0"]')]
    .filter(node => !node.closest('[hidden]') && node.getClientRects().length);

  const applyFeed = data => {
    let badge = toggle?.querySelector('b');
    if (toggle && !badge && data.unread) { badge = document.createElement('b'); toggle.append(badge); }
    if (badge) { badge.textContent = data.unread > 99 ? '99+' : String(data.unread); badge.hidden = !data.unread; }
    toggle?.setAttribute('aria-label', data.unread ? 'Abrir notificações: ' + data.unread + ' não lidas' : 'Abrir notificações');
    if (data.unread > knownUnread) window.chamasNotify?.('Você tem novas notificações na Arena.');
    knownUnread = data.unread;
    document.querySelectorAll('[data-notification-list]').forEach(list => {
      const focused = list.contains(document.activeElement) ? document.activeElement : null;
      const key = focused?.closest('[data-notification-id]')?.dataset.notificationId;
      const action = focused?.closest('form')?.getAttribute('action');
      const href = focused?.getAttribute('href');
      const name = focused?.getAttribute('name'), value = focused?.getAttribute('value');
      list.innerHTML = data.html;
      // A completed duel must disappear even when its old action has focus.
      if (focused) {
        const row = [...list.querySelectorAll('[data-notification-id]')].find(node => node.dataset.notificationId === key);
        const replacement = row && [...row.querySelectorAll('a,button')].find(node =>
          href ? node.getAttribute('href') === href :
            node.closest('form')?.getAttribute('action') === action &&
            node.getAttribute('name') === name && node.getAttribute('value') === value);
        (replacement || notifications?.querySelector('[data-notification-close]') || toggle)?.focus({preventScroll:true});
      }
    });
    feedCursor = data.cursor;
  };

  const refreshFeed = async (force = false) => {
    if (!feedEnabled || feedBusy || document.hidden || (!force && Date.now() - lastFeed < feedDelay)) return;
    feedBusy = true; lastFeed = Date.now();
    const abort = new AbortController(); feedAbort = abort;
    const timeout = setTimeout(() => abort.abort(), 8000);
    try {
      const response = await fetch('/api/notificacoes?cursor=' + encodeURIComponent(feedCursor), {signal:abort.signal, cache:'no-store', credentials:'same-origin'});
      if (response.status === 401) { feedEnabled = false; return; }
      if (response.status === 204) { feedDelay = 3000; return; }
      if (!response.ok) throw new Error('Feed unavailable');
      const data = await response.json();
      applyFeed(data); feedDelay = 3000;
    } catch (_) {
      feedDelay = Math.min(30000, feedDelay * 2);
    } finally { clearTimeout(timeout); feedBusy = false; }
  };

  const setNotificationsOpen = (open, restore = false) => {
    if (!notifications) return;
    notifications.hidden = !open;
    toggle?.setAttribute('aria-expanded', String(open));
    if (open) { refreshFeed(true); notifications.querySelector('[data-notification-close]')?.focus(); }
    else if (restore) toggle?.focus();
  };
  const closeModal = () => {
    if (!modal || modal.hidden) return;
    requestNumber++;
    controller?.abort();
    modal.hidden = true; modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = previousOverflow;
    if (opener?.isConnected) opener.focus();
  };
  const showProfile = async trigger => {
    if (!modal || !content) return;
    if (modal.hidden) { opener = trigger; previousOverflow = document.body.style.overflow; }
    retryTrigger = trigger;
    controller?.abort(); controller = new AbortController();
    const thisRequest = ++requestNumber;
    const activeController = controller;
    setNotificationsOpen(false);
    modal.hidden = false; modal.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden';
    content.innerHTML = '<div class="profile-modal-loading" role="status">Carregando perfil…</div>';
    modal.querySelector('.profile-modal-close')?.focus();
    const timeout = setTimeout(() => activeController.abort(), 15000);
    try {
      const response = await fetch(trigger.dataset.profileCardUrl, {signal:activeController.signal, headers:{'X-Requested-With':'fetch'}, cache:'no-store'});
      if (!response.ok) throw new Error();
      const html = await response.text();
      if (thisRequest !== requestNumber || modal.hidden) return;
      content.innerHTML = html;
      document.dispatchEvent(new CustomEvent('chamas:content', {detail:{container:content}}));
    } catch (_) {
      if (thisRequest !== requestNumber || modal.hidden) return;
      content.innerHTML = '<div class="profile-modal-loading"><p>Não foi possível abrir este perfil.</p><button type="button" class="btn" data-retry-profile>Tentar novamente</button></div>';
    } finally { clearTimeout(timeout); }
  };

  document.addEventListener('click', async event => {
    const target = event.target;
    if (target.closest('[data-notification-toggle],[data-open-notifications]')) {
      event.preventDefault(); setNotificationsOpen(notifications?.hidden); return;
    }
    if (target.closest('[data-notification-close]')) { setNotificationsOpen(false,true); return; }
    if (notifications && !notifications.hidden && !target.closest('#notification-popover')) setNotificationsOpen(false);
    const trigger = target.closest('.profile-popup-trigger[data-profile-card-url]');
    if (trigger) { event.preventDefault(); showProfile(trigger); return; }
    if (target.closest('[data-retry-profile]') && retryTrigger) { showProfile(retryTrigger); return; }
    if (target.closest('[data-close-profile]')) closeModal();

    const copy = target.closest('[data-copy-link]');
    if (copy) {
      try {
        await navigator.clipboard.writeText(copy.dataset.copyLink);
        window.chamasNotify?.('Link copiado. Compartilhe com a comunidade!');
      } catch (_) { window.prompt('Copie este link:', copy.dataset.copyLink); }
    }
    const share = target.closest('[data-native-share]');
    if (share) {
      const data = {title:share.dataset.shareTitle, url:share.dataset.shareUrl};
      if (navigator.share) {
        try { await navigator.share(data); } catch (error) { if (error.name !== 'AbortError') window.prompt('Copie este link:',data.url); }
      } else {
        try { await navigator.clipboard.writeText(data.url); window.chamasNotify?.('Link copiado para compartilhar.'); }
        catch (_) { window.prompt('Copie este link:',data.url); }
      }
    }
  });
  document.addEventListener('keydown', event => {
    const active = modal && !modal.hidden ? modal : notifications && !notifications.hidden ? notifications : null;
    if (event.key === 'Escape') { closeModal(); if (notifications && !notifications.hidden) setNotificationsOpen(false,true); }
    if (event.key !== 'Tab' || !active) return;
    const nodes = focusable(active); if (!nodes.length) return;
    const first=nodes[0], last=nodes[nodes.length-1];
    if (event.shiftKey && (document.activeElement === first || !active.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && (document.activeElement === last || !active.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
  });

  const search = document.getElementById('arena-player-search');
  const grid = document.getElementById('arena-player-grid');
  if (search && grid) {
    const cards=[...grid.querySelectorAll('[data-player-name]')];
    const count=document.getElementById('arena-player-count');
    const empty=document.createElement('div'); empty.className='empty'; empty.hidden=true;
    empty.innerHTML='<h3>Nenhum jogador encontrado</h3><p>Tente outro nome ou limpe a busca.</p>';
    grid.after(empty);
    const normalize=value => value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('pt-BR').trim();
    const apply=() => {
      const term=normalize(search.value); let visible=0;
      cards.forEach(card => { card.hidden=!normalize(card.dataset.playerName).includes(term); if (!card.hidden) visible++; });
      empty.hidden=visible>0 || !cards.length;
      if (count) count.textContent=visible+' de '+cards.length+' jogadores';
    };
    search.addEventListener('input',apply); apply();
  }
  if (notifications) {
    setInterval(() => refreshFeed(),3000);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) refreshFeed(true); else feedAbort?.abort();
    });
    window.addEventListener('focus', () => refreshFeed(true));
    window.addEventListener('online', () => refreshFeed(true));
    window.addEventListener('pagehide', () => feedAbort?.abort());
    window.addEventListener('pageshow', () => refreshFeed(true));
    refreshFeed(true);
  }
})();
