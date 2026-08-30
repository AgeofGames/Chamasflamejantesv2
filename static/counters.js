(() => {
  const app = document.querySelector("[data-counter-guide]");
  if (!app) return;

  const pantheons = [
    { id: "Greek", label: "Gregos", mark: "Ω", color: "#d8b45f" },
    { id: "Egyptian", label: "Egípcios", mark: "𓂀", color: "#e8c66b" },
    { id: "Norse", label: "Nórdicos", mark: "ᛉ", color: "#7dc1d3" },
    { id: "Atlantean", label: "Atlantes", mark: "△", color: "#6ed5cf" },
    { id: "Chinese", label: "Chineses", mark: "龍", color: "#e97762" },
    { id: "Japanese", label: "Japoneses", mark: "日", color: "#f0a07b" },
    { id: "Aztec", label: "Astecas", mark: "◆", color: "#84ce75" },
  ];
  const categoryOrder = ["human", "hero", "myth", "siege", "naval", "titan"];
  const categoryMeta = {
    human: { title: "Unidades humanas", description: "Infantaria, cavalaria e longo alcance", icon: "⚔️" },
    hero: { title: "Heróis", description: "Especialistas contra unidades míticas", icon: "👑" },
    myth: { title: "Unidades míticas", description: "Criaturas, monstros e invocações", icon: "✨" },
    siege: { title: "Cerco", description: "Armas contra construções e alvos pesados", icon: "🎯" },
    naval: { title: "Unidades navais", description: "Navios, criaturas aquáticas e heróis do mar", icon: "🌊" },
    titan: { title: "Titã", description: "A unidade suprema de cada panteão", icon: "🛡️" },
  };
  const costMeta = {
    Food: ["🍖", "Comida"], Wood: ["🪵", "Madeira"], Gold: ["🪙", "Ouro"],
    Favor: ["✨", "Favor"], Pop: ["👨‍🌾", "Pop."],
  };

  const tabs = document.querySelector("#counter-pantheon-tabs");
  const search = document.querySelector("#counter-unit-search");
  const groups = document.querySelector("#counter-unit-groups");
  const loading = document.querySelector("#counter-loading");
  const rosterTitle = document.querySelector("#counter-roster-title");
  const rosterCount = document.querySelector("#counter-roster-count");
  const hunterGrid = document.querySelector("#counter-hunter-grid");
  const modal = document.querySelector("#counter-modal");
  const selectedBox = document.querySelector("#counter-selected-unit");
  const enemyTabs = document.querySelector("#counter-enemy-tabs");
  const targetGrid = document.querySelector("#counter-target-grid");
  const resultSummary = document.querySelector("#counter-result-summary");
  const emptyResult = document.querySelector("#counter-empty-result");

  let units = [];
  let currentPantheon = "Greek";
  let selectedUnit = null;
  let enemyPantheon = "Egyptian";

  const normalize = (value) => (value || "")
    .toLocaleLowerCase("pt-BR")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();

  const imageUrl = (unit) => {
    const filename = String(unit.image || "").split("/").pop();
    return `${app.dataset.iconsBase}${filename}`;
  };

  function pantheonInfo(id) {
    return pantheons.find((item) => item.id === id) || pantheons[0];
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function unitPortrait(unit, className = "") {
    const wrap = element("div", `god-portrait-wrap counter-unit-portrait ${className}`.trim());
    const img = element("img");
    img.src = imageUrl(unit);
    img.alt = `Ícone de ${unit.name} em Age of Mythology: Retold`;
    img.loading = "lazy";
    const shade = element("div", "god-card-shade");
    const pill = element("span", "pantheon-pill", unit.categoryLabel);
    wrap.append(img, shade, pill);
    return wrap;
  }

  function makeUnitCard(unit) {
    const card = element("button", "god-knowledge-card counter-unit-card");
    card.type = "button";
    card.append(unitPortrait(unit));

    const body = element("span", "god-card-body counter-unit-card-body");
    const title = element("span", "god-card-title counter-unit-title");
    const titleCopy = element("span");
    titleCopy.append(element("small", "", unit.age ? `${unit.age} • ${unit.pantheonLabel}` : unit.pantheonLabel));
    titleCopy.append(element("strong", "counter-unit-name", unit.name));
    const advantages = element("b", "", String(unit.counterRules.length));
    advantages.append(element("small", "", "vantagens"));
    title.append(titleCopy, advantages);
    body.append(title);
    body.append(element("p", "counter-unit-description", unit.description));
    const footer = element("span", "open-god", "VER COUNTERS");
    footer.append(element("b", "", "→"));
    body.append(footer);
    card.append(body);
    card.addEventListener("click", () => openUnit(unit));
    return card;
  }

  function renderPantheonTabs() {
    tabs.replaceChildren();
    pantheons.forEach((pantheon) => {
      const button = element("button", "knowledge-filter counter-pantheon-tab");
      button.type = "button";
      button.style.setProperty("--counter-pantheon", pantheon.color);
      button.classList.toggle("active", pantheon.id === currentPantheon);
      button.append(element("span", "counter-pantheon-mark", pantheon.mark));
      button.append(document.createTextNode(pantheon.label));
      button.addEventListener("click", () => {
        currentPantheon = pantheon.id;
        search.value = "";
        renderPantheonTabs();
        renderRoster();
      });
      tabs.append(button);
    });
  }

  function renderRoster() {
    const pantheon = pantheonInfo(currentPantheon);
    const query = normalize(search.value);
    const visible = units.filter((unit) => {
      if (unit.pantheon !== currentPantheon) return false;
      const text = normalize(`${unit.name} ${unit.description} ${unit.categoryLabel} ${(unit.gods || []).join(" ")}`);
      return !query || text.includes(query);
    });
    const total = units.filter((unit) => unit.pantheon === currentPantheon).length;
    rosterTitle.textContent = `ELENCO ${pantheon.label.toLocaleUpperCase("pt-BR")}`;
    rosterCount.textContent = query ? `${visible.length} de ${total} unidades encontradas` : `${total} unidades no elenco ${pantheon.label.toLocaleLowerCase("pt-BR")}`;
    groups.replaceChildren();

    categoryOrder.forEach((category) => {
      const categoryUnits = visible.filter((unit) => unit.category === category);
      if (!categoryUnits.length) return;
      const meta = categoryMeta[category];
      const section = element("section", "counter-unit-group");
      const heading = element("div", "counter-unit-group-heading");
      heading.append(element("span", "counter-group-icon", meta.icon));
      const copy = element("div");
      copy.append(element("h3", "", meta.title));
      copy.append(element("p", "", meta.description));
      heading.append(copy, element("strong", "", String(categoryUnits.length)));
      const grid = element("div", "god-card-grid counter-unit-grid");
      categoryUnits.forEach((unit) => grid.append(makeUnitCard(unit)));
      section.append(heading, grid);
      groups.append(section);
    });

    if (!visible.length) {
      const empty = element("div", "knowledge-empty counter-no-units");
      empty.append(element("span", "", "🏺"));
      empty.append(element("h2", "", "Nenhuma unidade encontrada"));
      empty.append(element("p", "", "Tente pesquisar outro nome, categoria ou deus."));
      groups.append(empty);
    }
  }

  function renderTitanHunters() {
    hunterGrid.replaceChildren();
    pantheons.forEach((pantheon, index) => {
      const hunter = units
        .filter((unit) => unit.pantheon === pantheon.id && !unit.isTitan && unit.category === "hero")
        .sort((a, b) => Number(b.titanDps || 0) - Number(a.titanDps || 0))[0];
      if (!hunter) return;
      const button = element("button", "counter-hunter-chip");
      button.type = "button";
      button.style.setProperty("--counter-pantheon", pantheon.color);
      button.append(element("span", "counter-hunter-rank", String(index + 1).padStart(2, "0")));
      const img = element("img");
      img.src = imageUrl(hunter);
      img.alt = "";
      img.loading = "lazy";
      button.append(img);
      const copy = element("span");
      copy.append(element("small", "", pantheon.label));
      copy.append(element("strong", "", hunter.name));
      button.append(copy, element("b", "", "🎯"));
      button.addEventListener("click", () => openUnit(hunter));
      hunterGrid.append(button);
    });
  }

  function matchingRules(source, target) {
    return (source.counterRules || []).filter((rule) => {
      if (rule.trait === "MilitaryUnit") return true;
      if (rule.trait === "NavalUnit") return target.attributes.includes("NavalUnit") || target.attributes.includes("Ship");
      return target.attributes.includes(rule.trait);
    });
  }

  function strengthLabel(rules) {
    const multiplier = Math.max(0, ...rules.map((rule) => Number(rule.multiplier || 0)));
    if (multiplier >= 8) return "Counter extremo";
    if (multiplier >= 4) return "Counter forte";
    if (multiplier > 1) return `Bônus ×${multiplier}`;
    return "Vantagem de classe";
  }

  function openUnit(unit) {
    selectedUnit = unit;
    enemyPantheon = (pantheons.find((item) => item.id !== unit.pantheon) || pantheons[0]).id;
    renderSelectedUnit();
    renderEnemyTabs();
    renderTargets();
    modal.hidden = false;
    document.body.classList.add("counter-modal-open");
    modal.querySelector(".counter-modal-close").focus();
  }

  function closeModal() {
    modal.hidden = true;
    selectedUnit = null;
    document.body.classList.remove("counter-modal-open");
  }

  function renderSelectedUnit() {
    selectedBox.replaceChildren();
    const portrait = unitPortrait(selectedUnit, "counter-unit-portrait-large");
    const copy = element("div", "counter-selected-copy");
    copy.append(element("span", "eyebrow", `${selectedUnit.pantheonLabel} • ${selectedUnit.categoryLabel}`));
    copy.append(element("h2", "", selectedUnit.name));
    copy.append(element("p", "", selectedUnit.description));
    if (selectedUnit.gods && selectedUnit.gods.length) {
      const gods = element("small", "counter-available-gods", "Disponível com: ");
      gods.append(element("strong", "", selectedUnit.gods.join(", ")));
      copy.append(gods);
    }
    const stats = element("div", "counter-selected-stats");
    if (selectedUnit.hp) {
      const hp = element("span", "");
      hp.append(element("b", "", String(selectedUnit.hp)), document.createTextNode(" ❤️ PV base"));
      stats.append(hp);
    }
    Object.entries(selectedUnit.cost || {}).filter(([key]) => key !== "Time").slice(0, 5).forEach(([key, value]) => {
      const meta = costMeta[key] || ["•", key];
      const stat = element("span", "");
      stat.append(element("b", "", String(value)), document.createTextNode(` ${meta[0]} ${meta[1]}`));
      stats.append(stat);
    });
    copy.append(stats);
    selectedBox.append(portrait, copy);
  }

  function renderEnemyTabs() {
    enemyTabs.replaceChildren();
    pantheons.forEach((pantheon) => {
      const button = element("button", "knowledge-filter counter-enemy-tab");
      button.type = "button";
      button.classList.toggle("active", pantheon.id === enemyPantheon);
      button.style.setProperty("--counter-pantheon", pantheon.color);
      button.append(element("span", "", pantheon.mark), document.createTextNode(pantheon.label));
      button.addEventListener("click", () => {
        enemyPantheon = pantheon.id;
        renderEnemyTabs();
        renderTargets();
      });
      enemyTabs.append(button);
    });
  }

  function makeTargetCard(target, rules) {
    const card = element("article", "god-knowledge-card counter-target-card");
    card.append(unitPortrait(target, "counter-target-portrait"));
    const body = element("div", "god-card-body counter-target-body");
    body.append(element("span", "counter-strength-badge", strengthLabel(rules)));
    body.append(element("h3", "", target.name));
    body.append(element("p", "", target.description));
    const ruleList = element("div", "counter-rule-list");
    rules.forEach((rule) => {
      const value = rule.multiplier && rule.multiplier > 1 ? `${rule.label} ×${rule.multiplier}` : rule.label;
      ruleList.append(element("span", "", value));
    });
    body.append(ruleList);
    card.append(body);
    return card;
  }

  function renderTargets() {
    const targets = units
      .filter((unit) => unit.pantheon === enemyPantheon)
      .map((unit) => ({ unit, rules: matchingRules(selectedUnit, unit) }))
      .filter((entry) => entry.rules.length)
      .sort((a, b) => {
        const aMultiplier = Math.max(0, ...a.rules.map((rule) => Number(rule.multiplier || 0)));
        const bMultiplier = Math.max(0, ...b.rules.map((rule) => Number(rule.multiplier || 0)));
        return bMultiplier - aMultiplier || categoryOrder.indexOf(a.unit.category) - categoryOrder.indexOf(b.unit.category);
      });
    const enemy = pantheonInfo(enemyPantheon);
    resultSummary.textContent = `${targets.length} alvo${targets.length === 1 ? "" : "s"} encontrado${targets.length === 1 ? "" : "s"} entre os ${enemy.label}.`;
    targetGrid.replaceChildren();
    targets.forEach(({ unit, rules }) => targetGrid.append(makeTargetCard(unit, rules)));
    emptyResult.hidden = targets.length !== 0;
  }

  search.addEventListener("input", renderRoster);
  document.querySelectorAll("[data-counter-close]").forEach((button) => button.addEventListener("click", closeModal));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeModal();
  });

  fetch(app.dataset.unitsUrl)
    .then((response) => {
      if (!response.ok) throw new Error("Não foi possível carregar o catálogo.");
      return response.json();
    })
    .then((catalog) => {
      units = catalog;
      loading.hidden = true;
      renderPantheonTabs();
      renderTitanHunters();
      renderRoster();
    })
    .catch(() => {
      loading.querySelector("h2").textContent = "Não foi possível carregar o guia";
      loading.querySelector("p").textContent = "Atualize a página e tente novamente.";
    });
})();
