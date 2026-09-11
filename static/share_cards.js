(() => {
  'use strict';
  const files = new WeakMap();
  const initialized = new WeakSet();
  const preparing = new WeakMap();
  const note = (button, message) => {
    const output = button.closest('.share-card-panel')?.querySelector('.share-card-feedback');
    if (output) output.textContent = message;
  };
  const download = button => {
    const link = document.createElement('a');
    link.href = button.dataset.cardDownload;
    link.download = 'chamas-flamejantes.jpg';
    document.body.append(link); link.click(); link.remove();
    note(button, 'Anexe o card baixado na conversa ou na rede social que preferir.');
  };
  const prepare = button => {
    if (files.has(button)) return Promise.resolve(files.get(button));
    if (preparing.has(button)) return preparing.get(button);
    const promise = (async () => {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 10000);
      try {
        const url = new URL(button.dataset.cardImage, window.location.href);
        if (url.origin !== window.location.origin) throw new Error('origin');
        const response = await fetch(url, {signal:controller.signal, credentials:'omit'});
        if (!response.ok || !response.headers.get('Content-Type')?.startsWith('image/jpeg')) throw new Error('image');
        const blob = await response.blob();
        if (!blob.size || blob.size > 2 * 1024 * 1024) throw new Error('size');
        const file = new File([blob], 'chamas-flamejantes-arena.jpg', {type:'image/jpeg'});
        files.set(button, file);
        return file;
      } finally { clearTimeout(timeout); preparing.delete(button); }
    })();
    preparing.set(button, promise);
    return promise;
  };
  const supported = () => typeof navigator.share === 'function' && typeof navigator.canShare === 'function' && typeof File === 'function';
  const initialize = container => container?.querySelectorAll('[data-card-share]').forEach(button => {
    if (initialized.has(button)) return;
    initialized.add(button);
    // Fetch before the click, so opening the device share sheet retains user activation.
    const warm = () => { if (supported()) prepare(button).catch(() => {}); };
    button.addEventListener('pointerenter', warm, {once:true});
    button.addEventListener('focus', warm, {once:true});
    const image = button.closest('.share-card-panel')?.querySelector('.share-card-preview img');
    if (image?.complete && image.naturalWidth) warm();
    else image?.addEventListener('load', warm, {once:true});
    button.addEventListener('click', async () => {
      if (button.disabled) return;
      if (!supported()) { download(button); return; }
      const file = files.get(button);
      if (!file) {
        button.disabled = true;
        button.setAttribute('aria-busy','true');
        note(button, 'Preparando a imagem…');
        try { await prepare(button); note(button, 'Card pronto. Toque novamente em Enviar imagem para escolher o aplicativo.'); }
        catch (_) { note(button, 'Não foi possível preparar a imagem. Tente novamente ou use Baixar card.'); }
        finally { button.disabled = false; button.removeAttribute('aria-busy'); }
        return;
      }
      const payload = {files:[file], title:button.dataset.cardTitle, text:button.dataset.cardTitle + ' — ' + button.dataset.cardLink};
      if (!navigator.canShare({files:[file]})) { download(button); return; }
      button.disabled = true;
      try { await navigator.share(payload); note(button, ''); }
      catch (error) { if (error.name !== 'AbortError') note(button, 'O aparelho não conseguiu compartilhar a imagem. Use Baixar card ou compartilhe o link.'); }
      finally { button.disabled = false; }
    });
  });
  initialize(document);
  document.addEventListener('chamas:content', event => initialize(event.detail?.container));
})();
