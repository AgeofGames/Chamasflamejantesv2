document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("profile-modal");
  const content = document.getElementById("profile-modal-content");

  const closeModal = () => {
    if (!modal) return;
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  };

  document.addEventListener("click", async (event) => {
    const trigger = event.target.closest(".profile-popup-trigger[data-profile-card-url]");
    if (trigger && modal && content) {
      event.preventDefault();
      modal.hidden = false;
      modal.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      content.innerHTML = '<div class="profile-modal-loading">Carregando perfil…</div>';
      try {
        const response = await fetch(trigger.dataset.profileCardUrl, {headers: {"X-Requested-With": "fetch"}});
        if (!response.ok) throw new Error();
        content.innerHTML = await response.text();
        const first = content.querySelector("button, a, input, textarea");
        if (first) first.focus();
      } catch (_) {
        content.innerHTML = '<div class="profile-modal-loading">Não foi possível abrir o perfil agora.</div>';
      }
      return;
    }

    if (event.target.closest("[data-close-profile]")) closeModal();

    const copy = event.target.closest("[data-copy-link]");
    if (copy) {
      try {
        await navigator.clipboard.writeText(copy.dataset.copyLink);
        const original = copy.textContent;
        copy.textContent = "Link copiado!";
        setTimeout(() => { copy.textContent = original; }, 1800);
      } catch (_) {
        window.prompt("Copie este link:", copy.dataset.copyLink);
      }
    }

    const nativeShare = event.target.closest("[data-native-share]");
    if (nativeShare) {
      const data = {title: nativeShare.dataset.shareTitle, url: nativeShare.dataset.shareUrl};
      if (navigator.share) {
        try { await navigator.share(data); } catch (_) {}
      } else {
        window.prompt("Copie este link e compartilhe:", data.url);
      }
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModal();
  });

  const search = document.getElementById("arena-player-search");
  if (search) {
    search.addEventListener("input", () => {
      const term = search.value.trim().toLocaleLowerCase("pt-BR");
      document.querySelectorAll("#arena-player-grid [data-player-name]").forEach((card) => {
        card.hidden = term && !card.dataset.playerName.includes(term);
      });
    });
  }
});
