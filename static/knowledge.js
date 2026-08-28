(() => {
  const normalize = (value) => (value || "")
    .toLocaleLowerCase("pt-BR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();

  const setupGodFilters = () => {
    const search = document.querySelector("#knowledge-search");
    const cards = [...document.querySelectorAll("[data-knowledge-card]")];
    const buttons = [...document.querySelectorAll("[data-knowledge-pantheon]")];
    if (!search || !cards.length) return;
    let pantheon = "all";
    const apply = () => {
      const query = normalize(search.value);
      let visible = 0;
      cards.forEach((card) => {
        const matchesText = !query || normalize(card.dataset.search).includes(query);
        const matchesPantheon = pantheon === "all" || card.dataset.pantheon === pantheon;
        const show = matchesText && matchesPantheon;
        card.hidden = !show;
        if (show) visible += 1;
      });
      const count = document.querySelector("#knowledge-result-count");
      if (count) count.textContent = `${visible} ${visible === 1 ? "deus disponível" : "deuses disponíveis"}`;
      const empty = document.querySelector("#knowledge-empty");
      if (empty) empty.hidden = visible !== 0;
    };
    buttons.forEach((button) => button.addEventListener("click", () => {
      pantheon = button.dataset.knowledgePantheon;
      buttons.forEach((item) => item.classList.toggle("active", item === button));
      apply();
    }));
    search.addEventListener("input", apply);
  };

  const setupBuildFilters = () => {
    const search = document.querySelector("#build-search");
    const cards = [...document.querySelectorAll("[data-build-card]")];
    const buttons = [...document.querySelectorAll("[data-build-tag]")];
    if (!search || !cards.length) return;
    let tag = "all";
    const apply = () => {
      const query = normalize(search.value);
      let visible = 0;
      cards.forEach((card) => {
        const matchesText = !query || normalize(card.dataset.search).includes(query);
        const matchesTag = tag === "all" || (card.dataset.tags || "").split(" ").includes(tag);
        const show = matchesText && matchesTag;
        card.hidden = !show;
        if (show) visible += 1;
      });
      const count = document.querySelector("#build-result-count");
      if (count) count.textContent = `${visible} ${visible === 1 ? "build encontrada" : "builds encontradas"}`;
      const empty = document.querySelector("#build-empty");
      if (empty) empty.hidden = visible !== 0;
    };
    buttons.forEach((button) => button.addEventListener("click", () => {
      tag = button.dataset.buildTag;
      buttons.forEach((item) => item.classList.toggle("active", item === button));
      apply();
    }));
    search.addEventListener("input", apply);
  };

  document.addEventListener("DOMContentLoaded", () => {
    setupGodFilters();
    setupBuildFilters();
  });
})();
