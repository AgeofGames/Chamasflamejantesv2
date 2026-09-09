/* Progressive enhancement. Content and forms work when JavaScript is unavailable. */
(() => {
  'use strict';
  const root = document.documentElement;
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  const readLocal = key => { try { return localStorage.getItem(key); } catch (_) { return null; } };
  const saveLocal = (key, value) => { try { localStorage.setItem(key, value); } catch (_) {} };
  const savedMotion = readLocal('chamas-motion');
  if (savedMotion === 'reduce') root.dataset.motion = 'reduce';
  const reduced = () => motionQuery.matches || root.dataset.motion === 'reduce';
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').trim();

  const notify = message => {
    const region = document.querySelector('.toast-region');
    if (!region) return;
    region.replaceChildren();
    const toast = document.createElement('div');
    toast.className = 'app-toast';
    toast.textContent = message;
    region.append(toast);
    setTimeout(() => toast.remove(), 5000);
  };
  window.chamasNotify = notify;

  const header = document.querySelector('.topbar');
  const menuToggle = document.querySelector('.mobile-nav-toggle');
  const nav = document.querySelector('#main-navigation');
  const closeNav = () => {
    header?.classList.remove('nav-open');
    menuToggle?.setAttribute('aria-expanded', 'false');
  };
  if (menuToggle && header) {
    closeNav();
    root.classList.add('nav-ready');
    menuToggle.addEventListener('click', () => {
      const open = header.classList.toggle('nav-open');
      menuToggle.setAttribute('aria-expanded', String(open));
    });
    if ('ResizeObserver' in window) {
      new ResizeObserver(entries => {
        root.style.setProperty('--header-height', `${Math.ceil(entries[0].borderBoxSize?.[0]?.blockSize || header.getBoundingClientRect().height)}px`);
      }).observe(header);
    }
  }
  document.addEventListener('click', event => {
    if (!event.target.closest('.topbar')) closeNav();
    document.querySelectorAll('.nav-drop[open]').forEach(drop => {
      if (!drop.contains(event.target)) drop.open = false;
    });
    const dismiss = event.target.closest('[data-dismiss-flash]');
    if (dismiss) dismiss.closest('.flash')?.remove();
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const openDrop = document.querySelector('.nav-drop[open]');
    if (openDrop) { openDrop.open = false; openDrop.querySelector('summary')?.focus(); }
    if (header?.classList.contains('nav-open')) { closeNav(); menuToggle?.focus(); }
  });
  nav?.addEventListener('click', event => { if (event.target.closest('a')) closeNav(); });

  // Observe once, then release each element. No scroll animation loop or hidden content.
  let observer;
  const observed = new WeakSet();
  const pendingEntrances = new Set();
  const entrances = container => {
    if (reduced() || !('IntersectionObserver' in window)) return;
    pendingEntrances.forEach(node => {
      if (!node.isConnected) { observer?.unobserve(node); pendingEntrances.delete(node); }
    });
    if (!observer) observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const node = entry.target;
        observer.unobserve(node);
        pendingEntrances.delete(node);
        if (reduced()) return;
        node.classList.add('motion-enter');
        setTimeout(() => node.classList.remove('motion-enter'), 850);
      });
    }, {threshold:0.05, rootMargin:'0px 0px -12px'});
    const selector = '.hero-content,.page-hero,.knowledge-hero-copy,.section-head,.mode-card,.feature,.god-knowledge-card,.build-library-card,.counter-guide-launch,.arena-step,.profile-battle-stats,.profile-owner-actions,.share-panel,.community-highlight,.community-form-card,.build-phase,.counter-unit-card,.admin-block,.duel-message-window,.duel-versus-card';
    container.querySelectorAll(selector).forEach((node, index) => {
      if (index > 160 || observed.has(node) || node.hidden) return;
      observed.add(node);
      pendingEntrances.add(node);
      node.style.setProperty('--enter-delay', `${Math.min(index % 3, 2) * 45}ms`);
      observer.observe(node);
    });
  };
  entrances(document);
  document.addEventListener('chamas:content', event => entrances(event.detail?.container || document));
  const refreshMotion = () => {
    document.querySelectorAll('[data-motion-toggle]').forEach(button => {
      button.setAttribute('aria-pressed', String(reduced()));
      button.textContent = reduced() ? 'Animações reduzidas' : 'Reduzir animações';
    });
    if (reduced()) document.querySelectorAll('.motion-enter').forEach(node => node.classList.remove('motion-enter'));
  };
  document.querySelectorAll('[data-motion-toggle]').forEach(button => button.addEventListener('click', () => {
    if (motionQuery.matches) { notify('As animações reduzidas acompanham a preferência do seu aparelho.'); return; }
    root.dataset.motion = root.dataset.motion === 'reduce' ? 'full' : 'reduce';
    saveLocal('chamas-motion', root.dataset.motion);
    refreshMotion();
  }));
  motionQuery.addEventListener?.('change', refreshMotion);
  refreshMotion();

  const bar = document.querySelector('.reading-progress i');
  const back = document.querySelector('.back-to-top');
  let scheduled = false;
  const updateScroll = () => {
    scheduled = false;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    if (bar) bar.style.transform = `scaleX(${max > 0 ? Math.min(1, window.scrollY / max) : 0})`;
    if (back) back.hidden = window.scrollY < 600;
  };
  const scheduleScroll = () => { if (!scheduled) { scheduled = true; requestAnimationFrame(updateScroll); } };
  window.addEventListener('scroll', scheduleScroll, {passive:true});
  window.addEventListener('resize', scheduleScroll, {passive:true});
  updateScroll();
  back?.addEventListener('click', () => { window.scrollTo({top:0, behavior:reduced() ? 'instant' : 'smooth'}); document.querySelector('.brand')?.focus({preventScroll:true}); });

  // Preserve named submitters; prevent repeated POSTs and restore on browser Back.
  document.addEventListener('submit', event => {
    const form = event.target;
    if (event.defaultPrevented || form.method.toLowerCase() !== 'post') return;
    if (form.dataset.submitting === 'true') { event.preventDefault(); return; }
    form.dataset.submitting = 'true';
    form.setAttribute('aria-busy','true');
    const submitter = event.submitter || form.querySelector('button[type=submit],button:not([type])');
    if (submitter) { submitter.setAttribute('aria-busy','true'); submitter.setAttribute('aria-disabled','true'); }
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('form[data-submitting]').forEach(form => {
      delete form.dataset.submitting; form.removeAttribute('aria-busy');
      form.querySelectorAll('[aria-busy]').forEach(button => { button.removeAttribute('aria-busy'); button.removeAttribute('aria-disabled'); });
    });
  });

  document.querySelectorAll('textarea[maxlength]').forEach(input => {
    const counter = document.createElement('small');
    counter.className = 'text-counter';
    input.after(counter);
    const update = () => { counter.textContent = `${input.value.length} / ${input.maxLength}`; };
    input.addEventListener('input', update); update();
  });
  const upload = document.querySelector('.profile-editor-form input[name=avatar]');
  if (upload) {
    let objectURL;
    const preview = document.createElement('div'); preview.className = 'avatar-local-preview'; preview.hidden = true; upload.after(preview);
    upload.addEventListener('change', () => {
      if (objectURL) URL.revokeObjectURL(objectURL);
      preview.replaceChildren(); preview.hidden = true; upload.setCustomValidity('');
      const file = upload.files?.[0]; if (!file) return;
      if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 8 * 1024 * 1024) {
        upload.setCustomValidity('Escolha uma foto JPG, PNG ou WebP de até 8 MB.'); upload.reportValidity(); return;
      }
      objectURL = URL.createObjectURL(file);
      const img = document.createElement('img'); img.src = objectURL; img.alt = 'Prévia da sua nova foto';
      const text = document.createElement('span'); text.textContent = 'Nova foto selecionada. Salve para aplicar.';
      preview.append(img, text); preview.hidden = false;
    });
  }

  // Add useful feedback to the existing search; map filtering remains unchanged.
  document.querySelectorAll('[data-quick-filter]').forEach(input => {
    const cards = [...document.querySelectorAll(input.dataset.quickFilter)];
    const count = document.getElementById(input.dataset.countTarget);
    const empty = document.getElementById(input.dataset.emptyTarget);
    const apply = () => {
      const term = normalize(input.value); let visible = 0;
      cards.forEach(card => { card.hidden = !normalize(card.dataset.filterText || card.textContent).includes(term); if (!card.hidden) visible++; });
      if (count) count.textContent = `${visible} de ${cards.length} resultados`;
      if (empty) empty.hidden = visible > 0;
    };
    input.addEventListener('input', apply); apply();
  });
  document.querySelectorAll('[data-clear-search]').forEach(button => button.addEventListener('click', () => {
    const input = document.getElementById(button.dataset.clearSearch);
    if (input) { input.value = ''; input.dispatchEvent(new Event('input', {bubbles:true})); input.focus(); }
  }));
  document.querySelectorAll('.map-filter,.knowledge-filter').forEach(button => {
    button.setAttribute('aria-pressed', String(button.classList.contains('active')));
    button.addEventListener('click', () => { queueMicrotask(() => button.parentElement.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item.classList.contains('active'))))); });
  });

  // Study checklist stays on this device and never changes a published build.
  const steps = [...document.querySelectorAll('.build-timeline .phase-step')];
  const sidebar = document.querySelector('.build-guide-sidebar');
  if (steps.length && sidebar) {
    const key = `chamas-build:${window.location.pathname}`;
    let done = [];
    try { const saved = JSON.parse(readLocal(key) || '[]'); if (Array.isArray(saved)) done = saved.filter(n => Number.isInteger(n) && n >= 0 && n < steps.length); } catch (_) {}
    const tools = document.createElement('section'); tools.className = 'build-progress-tools';
    const text = document.createElement('p'); const progress = document.createElement('progress'); progress.max = steps.length; progress.setAttribute('aria-label','Etapas estudadas');
    const reset = document.createElement('button'); reset.type='button'; reset.textContent='Reiniciar estudo';
    tools.append(text,progress,reset); sidebar.append(tools);
    const refresh = () => { progress.value = done.length; text.textContent = `${done.length} de ${steps.length} passos concluídos · salvo neste navegador`; saveLocal(key,JSON.stringify(done)); };
    steps.forEach((step,index) => {
      const label = document.createElement('label'); label.className='step-check';
      const checkbox = document.createElement('input'); checkbox.type='checkbox'; checkbox.checked=done.includes(index);
      label.append(checkbox,document.createTextNode('Concluí este passo')); step.append(label); step.classList.toggle('step-done',checkbox.checked);
      checkbox.addEventListener('change', () => { done = done.filter(n => n !== index); if (checkbox.checked) done.push(index); step.classList.toggle('step-done',checkbox.checked); refresh(); });
    });
    reset.addEventListener('click', () => { done=[]; steps.forEach(step => { step.classList.remove('step-done'); step.querySelector('.step-check input').checked=false; }); refresh(); notify('Seu estudo desta build foi reiniciado.'); });
    refresh();
  }
})();
