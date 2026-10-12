const STORAGE_KEY = "dnd-core-character-draft-v1";
const APP_STEPS = [
  { title: "Identidade", subtitle: "Quem atravessa o limiar?" },
  { title: "Origem", subtitle: "Espécie e antecedente" },
  { title: "Atributos", subtitle: "Forje suas capacidades" },
  { title: "Classe", subtitle: "Treino e características" },
  { title: "Magia", subtitle: "Conjuração e escolhas" },
  { title: "Revisão", subtitle: "Confira antes de criar" },
];
const ABILITY_ORDER = ["forca", "destreza", "constituicao", "inteligencia", "sabedoria", "carisma"];
const ABILITY_SKILLS = {
  forca: "Força", destreza: "Destreza", constituicao: "Constituição", inteligencia: "Inteligência",
  sabedoria: "Sabedoria", carisma: "Carisma",
};
const STAT_SKILL_LABELS = {
  acrobacia: "Acrobacia", adestrar_animais: "Adestrar Animais", arcanismo: "Arcanismo", atletismo: "Atletismo",
  atuacao: "Atuação", enganacao: "Enganação", furtividade: "Furtividade", historia: "História",
  intimidacao: "Intimidação", intuicao: "Intuição", investigacao: "Investigação", medicina: "Medicina",
  natureza: "Natureza", percepcao: "Percepção", persuasao: "Persuasão", prestidigitacao: "Prestidigitação",
  religiao: "Religião", sobrevivencia: "Sobrevivência",
};
const CLASS_TRANSLATIONS = {
  barbaro: "Bárbaro", bardo: "Bardo", clerigo: "Clérigo", druida: "Druida", guerreiro: "Guerreiro",
  monge: "Monge", paladino: "Paladino", guardiao: "Guardião", ladino: "Ladino", feiticeiro: "Feiticeiro",
  bruxo: "Bruxo", mago: "Mago", artifice: "Artífice",
};
const SPECIES_TRANSLATIONS = {
  aasimar: "Aasimar", anao: "Anão", draconato: "Draconato", elfo: "Elfo", gnomo: "Gnomo", golias: "Golias",
  halfling: "Pequenino", humano: "Humano", orc: "Orc", tiefling: "Tiefling",
};

const appRoot = document.getElementById("app");
let catalog = null;
let apiOnline = false;
let currentStep = 0;
let previewResult = null;
let scoreResult = null;
let scoreError = "";
let serviceError = "";
let savedCharacters = [];
let isCreating = false;
let createdRecord = null;
let previewTimer = null;
let scoreTimer = null;
let previewRequest = 0;
let scoreRequest = 0;
let modalOpen = false;
let draftStorage = "local";

function emptyDraft(abilityScores = null) {
  return {
    version: 1,
    step: 0,
    name: "",
    pronouns: "",
    species: "",
    class: "",
    background: "",
    ravenloft: false,
    abilityMethod: "standard_array",
    abilityScores: abilityScores || Object.fromEntries(ABILITY_ORDER.map((key, index) => [key, [15, 14, 13, 12, 10, 8][index]])),
    increaseModeByBackground: {},
    increasePicksByBackground: {},
    equipmentByBackground: {},
    toolByBackground: {},
    backgroundFeatByBackground: {},
    speciesChoiceBySpecies: {},
    speciesSkillBySpecies: {},
    sizeBySpecies: {},
    speciesFeat: "",
    classSkillsByClass: {},
    classChoicesByClass: {},
    expertiseByClass: {},
    spellsByClass: {},
    artisanToolProficiency: "",
    narrative: { appearance: "", backstory: "", motive: "" },
  };
}

function loadDraft() {
  let draft = null;
  let stored = null;
  let localAvailable = true;
  try { stored = localStorage.getItem(STORAGE_KEY); }
  catch (error) { localAvailable = false; console.warn("Armazenamento local persistente indisponível; tentando a sessão atual.", error); }
  if (stored) {
    try { draft = JSON.parse(stored); }
    catch (error) { console.warn("O rascunho local está inválido e será ignorado.", error); }
  } else {
    try {
      stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) { draft = JSON.parse(stored); draftStorage = "session"; }
      else if (!localAvailable) draftStorage = "session";
    } catch (error) {
      console.warn("O rascunho só poderá ser mantido em memória nesta sessão.", error);
      draftStorage = "memory";
    }
  }
  const base = emptyDraft(catalog?.score_methods?.standard_array?.assignment || null);
  if (!draft || typeof draft !== "object" || draft.version !== 1) return base;
  const merged = { ...base, ...draft };
  merged.step = Number.isInteger(merged.step) ? Math.max(0, Math.min(APP_STEPS.length - 1, merged.step)) : 0;
  merged.abilityScores = { ...base.abilityScores, ...(isObject(merged.abilityScores) ? merged.abilityScores : {}) };
  merged.narrative = { ...base.narrative, ...(isObject(merged.narrative) ? merged.narrative : {}) };
  for (const key of [
    "increaseModeByBackground", "increasePicksByBackground", "equipmentByBackground", "toolByBackground",
    "backgroundFeatByBackground", "speciesChoiceBySpecies", "speciesSkillBySpecies", "sizeBySpecies",
    "classSkillsByClass", "classChoicesByClass", "expertiseByClass", "spellsByClass",
  ]) if (!isObject(merged[key])) merged[key] = {};
  return merged;
}

let state = emptyDraft();

function isObject(value) { return Boolean(value) && typeof value === "object" && !Array.isArray(value); }
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
function normalize(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}
function humanize(value) {
  const key = normalize(value);
  return ABILITY_SKILLS[key] || STAT_SKILL_LABELS[key] || CLASS_TRANSLATIONS[key] || SPECIES_TRANSLATIONS[key] ||
    key.split("_").filter(Boolean).map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ") || String(value ?? "");
}
function classData(key = state.class) { return catalog?.classes?.find((item) => item.key === key) || null; }
function speciesData(key = state.species) { return catalog?.species?.find((item) => item.key === key) || null; }
function backgroundData(key = state.background) { return catalog?.backgrounds?.find((item) => item.key === key) || null; }
function currentProfile() { return previewResult?.profile?.class === state.class ? previewResult.profile : null; }
function classChoices() { return state.classChoicesByClass[state.class] || (state.classChoicesByClass[state.class] = {}); }
function classSkills() { return state.classSkillsByClass[state.class] || (state.classSkillsByClass[state.class] = []); }
function expertise() { return state.expertiseByClass[state.class] || (state.expertiseByClass[state.class] = []); }
function spellSelections() {
  if (!state.spellsByClass[state.class]) state.spellsByClass[state.class] = { cantrips: [], selected: [], spellbook: [] };
  const entry = state.spellsByClass[state.class];
  for (const key of ["cantrips", "selected", "spellbook"]) if (!Array.isArray(entry[key])) entry[key] = [];
  return entry;
}
function currentIncreases() {
  const background = state.background;
  const mode = state.increaseModeByBackground[background] || "two";
  const picks = state.increasePicksByBackground[background] || [];
  const values = {};
  picks.forEach((ability, index) => {
    if (ABILITY_ORDER.includes(ability)) values[ability] = (values[ability] || 0) + (mode === "two" && index === 0 ? 2 : 1);
  });
  return values;
}
function finalScore(ability) { return Number(state.abilityScores[ability] || 0) + Number(currentIncreases()[ability] || 0); }
function currentSpeciesChoice() { return state.speciesChoiceBySpecies[state.species] || ""; }
function currentSpeciesSkill() { return state.speciesSkillBySpecies[state.species] || ""; }
function currentSize() { return state.sizeBySpecies[state.species] || ""; }
function currentClassSkills() { return classSkills(); }
function currentBackgroundFeat() { return state.backgroundFeatByBackground[state.background] || ""; }
function currentBackgroundTool() { return state.toolByBackground[state.background] || ""; }
function currentEquipment() { return state.equipmentByBackground[state.background] || ""; }
function saveDraft() {
  state.step = currentStep;
  const serialized = JSON.stringify(state);
  try {
    localStorage.setItem(STORAGE_KEY, serialized);
    draftStorage = "local";
  } catch (error) {
    try {
      sessionStorage.setItem(STORAGE_KEY, serialized);
      draftStorage = "session";
    } catch (sessionError) {
      draftStorage = "memory";
      console.warn("O rascunho só está na memória desta aba.", sessionError || error);
    }
  }
  updateLiveSummary();
}

async function requestJSON(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  let data;
  try { data = await response.json(); }
  catch { data = { error: `Resposta inválida do serviço (${response.status}).` }; }
  if (!response.ok) {
    const error = new Error(data.error || `Falha de comunicação (${response.status}).`);
    error.status = response.status;
    error.field = data.field;
    throw error;
  }
  return data;
}

function payloadFromState() {
  const background = backgroundData();
  const backgroundFeat = currentBackgroundFeat();
  const speciesChoice = currentSpeciesChoice();
  const spells = state.spellsByClass[state.class] || { cantrips: [], selected: [], spellbook: [] };
  return {
    name: state.name,
    class: state.class,
    species: state.species,
    background: state.background,
    ravenloft: Boolean(state.ravenloft),
    ability_method: state.abilityMethod,
    ability_scores: state.abilityScores,
    background_increases: background ? currentIncreases() : {},
    background_tool: currentBackgroundTool(),
    background_equipment: currentEquipment(),
    background_feat: backgroundFeat,
    species_choice: speciesChoice,
    species_skill: currentSpeciesSkill(),
    size: currentSize(),
    species_feat: state.speciesFeat,
    class_skills: currentClassSkills(),
    class_choices: state.classChoicesByClass[state.class] || {},
    expertise: expertise(),
    artisan_tool_proficiency: state.artisanToolProficiency,
    spells: {
      cantrips: Array.isArray(spells.cantrips) ? spells.cantrips : [],
      selected: Array.isArray(spells.selected) ? spells.selected : [],
      spellbook: Array.isArray(spells.spellbook) ? spells.spellbook : [],
    },
    narrative: {
      pronouns: state.pronouns,
      appearance: state.narrative.appearance,
      backstory: state.narrative.backstory,
      motive: state.narrative.motive,
    },
  };
}

function updateConnection(online, message = "") {
  apiOnline = online;
  const connection = document.querySelector("#connection-state");
  const banner = document.querySelector("#connection-banner");
  if (connection) {
    connection.classList.toggle("offline", !online);
    const text = connection.querySelector("[data-connection-label]");
    if (text) text.textContent = online ? "Motor conectado" : "Motor indisponível";
  }
  if (banner) {
    banner.hidden = online;
    banner.textContent = online ? "" : (message || "Não foi possível falar com o motor. Seu rascunho continua salvo neste dispositivo; tente novamente quando a conexão voltar.");
  }
}

function schedulePreview({ immediate = false } = {}) {
  if (previewTimer) clearTimeout(previewTimer);
  previewTimer = setTimeout(refreshPreview, immediate ? 0 : 320);
}
function scheduleScorePreview({ immediate = false } = {}) {
  if (scoreTimer) clearTimeout(scoreTimer);
  scoreTimer = setTimeout(refreshScorePreview, immediate ? 0 : 220);
}

async function refreshPreview() {
  const sequence = ++previewRequest;
  try {
    const result = await requestJSON("/api/preview", { method: "POST", body: JSON.stringify(payloadFromState()) });
    if (sequence !== previewRequest) return;
    previewResult = result;
    serviceError = "";
    updateConnection(true);
    updateLiveSummary();
    renderPreviewStatus();
    if ([3, 4, 5].includes(currentStep)) renderMainPanel();
  } catch (error) {
    if (sequence !== previewRequest) return;
    serviceError = error.message;
    updateConnection(error.status !== undefined, error.message);
    updateLiveSummary();
    renderPreviewStatus();
  }
}

async function refreshScorePreview() {
  const sequence = ++scoreRequest;
  scoreResult = null;
  scoreError = "";
  updateScoreLedger();
  try {
    const result = await requestJSON("/api/score-preview", {
      method: "POST",
      body: JSON.stringify({ method: state.abilityMethod, ability_scores: state.abilityScores }),
    });
    if (sequence !== scoreRequest) return;
    scoreResult = result;
    scoreError = "";
  } catch (error) {
    if (sequence !== scoreRequest) return;
    scoreResult = null;
    scoreError = error.message;
  }
  updateScoreLedger();
}

function updateScoreLedger() {
  const ledger = document.querySelector("#point-ledger");
  if (!ledger) return;
  const text = ledger.querySelector("[data-points-message]");
  const points = ledger.querySelector("[data-points-value]");
  ledger.classList.toggle("invalid", Boolean(scoreError));
  if (scoreError) {
    if (text) text.textContent = scoreError;
    if (points) points.textContent = "—";
  } else if (state.abilityMethod === "point_buy" && scoreResult) {
    if (text) text.textContent = `Compra por pontos · ${scoreResult.points_spent} de 27 usados`;
    if (points) points.textContent = `${scoreResult.points_remaining} restantes`;
  } else if (scoreResult) {
    if (text) text.textContent = "Matriz padrão conferida pelo Rule Engine";
    if (points) points.textContent = "Matriz válida";
  } else {
    if (text) text.textContent = "Conferindo a distribuição…";
    if (points) points.textContent = "…";
  }
}

async function refreshSavedCharacters() {
  if (!apiOnline) return;
  try {
    const data = await requestJSON("/api/characters");
    savedCharacters = Array.isArray(data.items) ? data.items : [];
    updateSavedCount();
    if (modalOpen) renderSavedModal();
  } catch (error) {
    console.warn("Não foi possível carregar fichas salvas.", error);
  }
}

function updateSavedCount() {
  const badge = document.querySelector("[data-saved-count]");
  if (badge) badge.textContent = savedCharacters.length ? `Minhas fichas · ${savedCharacters.length}` : "Minhas fichas";
}

function renderApp() {
  if (!catalog) return;
  const draftExists = Boolean(state.name || state.class || state.species || state.background);
  appRoot.innerHTML = `
    <div class="app-shell">
      <header class="topbar">
        <div class="brand">
          <div class="brand-mark" aria-hidden="true">✦</div>
          <div class="brand-copy"><strong>Ateliê de Heróis</strong><span>D&amp;D · Edição 2024</span></div>
        </div>
        <div class="top-actions">
          <div id="connection-state" class="connection-state ${apiOnline ? "" : "offline"}" role="status">
            <span class="connection-dot" aria-hidden="true"></span><span data-connection-label>${apiOnline ? "Motor conectado" : "Conectando…"}</span>
          </div>
          <button class="quiet-button" type="button" data-action="saved-list" data-saved-count>Minhas fichas</button>
          ${draftExists ? '<button class="quiet-button" type="button" data-action="new-draft">Novo rascunho</button>' : ""}
        </div>
      </header>
      <section class="hero-banner" aria-label="Ateliê de criação">
        <div class="hero-copy">
          <div class="eyebrow">Seu próximo capítulo começa aqui</div>
          <h1>Um nome. Uma origem. Um destino.</h1>
          <p>Crie com escolhas conferidas pelo motor de regras. Seu rascunho acompanha cada passo — e só vira ficha depois de ser salvo.</p>
        </div>
      </section>
      <div id="connection-banner" class="connection-banner" role="alert" ${apiOnline ? "hidden" : ""}>${esc(serviceError || "Conectando ao serviço de criação…")}</div>
      <div id="service-error" class="error-banner" role="alert" hidden></div>
      <nav class="mobile-stepbar" aria-label="Etapas da criação">${renderMobileSteps()}</nav>
      <div class="workspace">
        <nav class="steps-rail" aria-label="Etapas da criação">
          <p class="rail-title">Sua jornada</p>
          <div class="step-list">${renderSteps()}</div>
          <p class="rail-footnote">Você pode voltar e corrigir qualquer escolha. O rascunho é salvo neste dispositivo.</p>
        </nav>
        <main id="main-panel" class="main-panel" tabindex="-1">${renderMainPanelMarkup()}</main>
        <aside class="side-rail" aria-label="Resumo do personagem">
          <section class="side-card">
            <h3>Registro de viagem</h3>
            <div id="live-summary">${renderLiveSummary()}</div>
          </section>
          <section class="side-card">
            <h3>Leitura do motor</h3>
            <div id="live-readiness">${renderReadiness()}</div>
            <p class="side-help">O motor valida pré-requisitos e regras. Se algo não estiver implementado, a ficha mostra a limitação em vez de presumir uma resposta.</p>
          </section>
          <section class="side-card">
            <h3>O que fica registrado</h3>
            <div class="live-ledger">
              <div class="ledger-item"><span>Nível</span><span>1</span></div>
              <div class="ledger-item"><span>Regras</span><span>Motor do projeto</span></div>
              <div class="ledger-item"><span>Estado</span><span data-persist-state>${createdRecord ? "Salvo" : draftStorage === "session" ? "Rascunho da sessão" : draftStorage === "memory" ? "Rascunho temporário" : "Rascunho local"}</span></div>
            </div>
          </section>
        </aside>
      </div>
      <div id="saved-modal-root"></div>
    </div>`;
  updateSavedCount();
  updateScoreLedger();
  renderPreviewStatus();
}

function renderMobileSteps() {
  return APP_STEPS.map((step, index) => `<button type="button" class="${index === currentStep ? "active" : ""}" data-step="${index}" aria-current="${index === currentStep ? "step" : "false"}">${index + 1} · ${esc(step.title)}</button>`).join("");
}
function fieldBelongsToStep(field, index) {
  if (index === 0) return ["name", "class", "species", "ravenloft"].includes(field);
  if (index === 1) return ["background", "background_increases", "background_tool", "background_equipment", "background_feat", "species_choice", "species_skill", "size", "species_feat"].includes(field);
  if (index === 2) return ["ability_scores", "ability_method"].includes(field);
  if (index === 3) return ["class_skills", "artisan_tool_proficiency", "expertise"].includes(field) || field.startsWith("class_choices.");
  if (index === 4) return field.startsWith("spells");
  return false;
}
function stepHasError(index) {
  const missing = previewResult?.missing || [];
  return missing.some((item) => fieldBelongsToStep(item.field, index));
}
function stepIsComplete(index) { return Boolean(previewResult?.ready) || Boolean(previewResult && !stepHasError(index) && index < 5); }
function renderSteps() {
  return APP_STEPS.map((step, index) => {
    const isComplete = stepIsComplete(index) && index !== currentStep;
    return `<button type="button" class="step-link ${index === currentStep ? "active" : ""} ${isComplete ? "complete" : ""}" data-step="${index}" aria-current="${index === currentStep ? "step" : "false"}">
      <span class="step-number">${isComplete ? "✓" : String(index + 1).padStart(2, "0")}</span>
      <span class="step-name">${esc(step.title)}<small>${esc(step.subtitle)}</small></span>
    </button>`;
  }).join("");
}

function renderMainPanelMarkup() {
  const section = renderStepContent(currentStep);
  const isLast = currentStep === APP_STEPS.length - 1;
  const previous = currentStep > 0 ? `<button class="secondary-button" type="button" data-action="previous"><span class="button-icon">←</span> Voltar</button>` : `<span class="footer-note">Rascunho salvo automaticamente neste dispositivo.</span>`;
  let next = "";
  if (isLast) {
    next = createdRecord
      ? `<button class="primary-button" type="button" data-action="new-draft"><span class="button-icon">✦</span> Criar outro personagem</button>`
      : `<button class="primary-button" type="button" data-action="create" ${!previewResult?.ready || isCreating || !apiOnline ? "disabled" : ""}>${isCreating ? "Salvando…" : "Confirmar e criar ficha"}<span class="button-icon">✦</span></button>`;
  } else {
    next = `<button class="primary-button" type="button" data-action="next">${currentStep === 4 ? "Conferir ficha" : "Continuar"}<span class="button-icon">→</span></button>`;
  }
  return `
    <div class="panel-header">
      <div class="panel-header-row">
        <div><div class="section-kicker">Etapa ${String(currentStep + 1).padStart(2, "0")} · ${esc(APP_STEPS[currentStep].title)}</div><h2>${esc(APP_STEPS[currentStep].title)}</h2><p>${esc(stepIntro(currentStep))}</p></div>
        <span class="step-counter">${currentStep + 1} / ${APP_STEPS.length}</span>
      </div>
      <div class="step-mobile-progress" aria-hidden="true"><span class="progress-fill progress-${currentStep + 1}"></span></div>
    </div>
    <div class="panel-body">${section}</div>
    <footer class="panel-footer"><div class="footer-note">${currentStep === 5 && !createdRecord ? "Nada será criado antes da confirmação do armazenamento." : "Suas escolhas permanecem no rascunho enquanto você navega."}</div><div class="button-row">${previous}${next}</div></footer>`;
}

function renderMainPanel() {
  const main = document.querySelector("#main-panel");
  if (!main) return;
  main.innerHTML = renderMainPanelMarkup();
  renderPreviewStatus();
  updateScoreLedger();
}

function stepIntro(index) {
  return [
    "Dê forma à presença que o mundo vai conhecer.",
    "Escolha as marcas que vieram antes da aventura.",
    "Distribua os atributos e veja o custo conferido pelo motor.",
    "Descubra o que sua classe oferece no primeiro nível.",
    "Escolha apenas as magias que o catálogo do motor reconhece.",
    "Leia a ficha, as validações e os limites de cobertura antes de salvar.",
  ][index];
}

function renderStepContent(index) {
  if (index === 0) return renderIdentityStep();
  if (index === 1) return renderOriginStep();
  if (index === 2) return renderAbilityStep();
  if (index === 3) return renderClassStep();
  if (index === 4) return renderMagicStep();
  return renderReviewStep();
}

function renderIdentityStep() {
  const raceCards = catalog.species.map((species) => `
    <button type="button" class="choice-card ${state.species === species.key ? "selected" : ""}" data-choice-field="species" data-value="${esc(species.key)}" aria-pressed="${state.species === species.key}">
      <strong>${esc(species.label)}</strong>
      <span>${esc((species.traits || []).slice(0, 2).map((trait) => trait.name).filter(Boolean).join(" · ") || "Espécie do catálogo do motor")}</span>
      <small>${species.speed_m ? `${esc(species.speed_m)} m de deslocamento` : "Traços consultados no Rule Engine"}</small>
    </button>`).join("");
  return `
    <section class="form-section">
      <h3>O nome que será lembrado</h3>
      <p>Comece com a identidade. Nada nesta etapa altera as regras da ficha.</p>
      <div class="field-grid">
        <div class="field"><label for="character-name">Nome do personagem</label><input id="character-name" class="text-input" data-text="name" maxlength="80" placeholder="Ex.: Elira Ventoferro" value="${esc(state.name)}" autocomplete="off" /></div>
        <div class="field"><label for="character-pronouns">Pronomes <span class="muted">· opcional</span></label><input id="character-pronouns" class="text-input" data-text="pronouns" maxlength="60" placeholder="Ex.: ela/dela" value="${esc(state.pronouns)}" /></div>
      </div>
    </section>
    <details class="form-section narrative-details">
      <summary class="subsection-title">Detalhes pessoais e passado <span class="muted">· opcional</span></summary>
      <p>Estas notas narrativas são salvas junto à ficha, sem alterar cálculos mecânicos.</p>
      <div class="field-grid">
        <div class="field"><label for="appearance">Aparência</label><textarea id="appearance" class="text-area" data-text="appearance" maxlength="500" placeholder="Marcas, vestes, presença…">${esc(state.narrative.appearance)}</textarea></div>
        <div class="field"><label for="motive">Motivação</label><textarea id="motive" class="text-area" data-text="motive" maxlength="500" placeholder="O que não pode deixar para trás?">${esc(state.narrative.motive)}</textarea></div>
      </div>
      <div class="field mt-16"><label for="backstory">História breve</label><textarea id="backstory" class="text-area" data-text="backstory" maxlength="2000" placeholder="Uma lembrança, um juramento, uma dívida…">${esc(state.narrative.backstory)}</textarea></div>
    </details>
    <section class="form-section">
      <div class="panel-header-row"><div><h3>Escolha sua espécie</h3><p class="no-margin">Os traços e escolhas vêm do catálogo de espécies do motor.</p></div><span class="source-tag">10 opções no catálogo</span></div>
      <div class="choice-grid three mt-16">${raceCards}</div>
    </section>
    <section class="form-section">
      <div class="toggle-row">
        <div class="toggle-copy"><strong>Permitir conteúdo de Ravenloft</strong><span>Habilita antecedentes, talentos e opções de origem dessa fonte. Nada será ativado sem sua escolha.</span></div>
        <label class="toggle" aria-label="Permitir conteúdo de Ravenloft"><input type="checkbox" data-field="ravenloft" ${state.ravenloft ? "checked" : ""}><span class="toggle-track"></span></label>
      </div>
    </section>`;
}

function renderOriginStep() {
  const visibleBackgrounds = catalog.backgrounds.filter((item) => state.ravenloft || !item.requires_ravenloft);
  const backgroundCards = visibleBackgrounds.map((item) => `
    <button type="button" class="choice-card ${state.background === item.key ? "selected" : ""}" data-choice-field="background" data-value="${esc(item.key)}" aria-pressed="${state.background === item.key}">
      <strong>${esc(item.label)}</strong>
      <span>${(item.skills || []).map((skill) => esc(skill.label)).join(" · ")}${item.feat_label ? ` · ${esc(item.feat_label)}` : ""}</span>
      <small>${esc(item.source)}${item.requires_ravenloft ? " · conteúdo opcional" : ""}</small>
    </button>`).join("");
  const bg = backgroundData();
  const race = speciesData();
  return `
    <section class="form-section">
      <h3>Antecedente</h3><p>Seu antecedente define perícias, talento, equipamento e os atributos entre os quais distribuir os aumentos.</p>
      <div class="choice-grid">${backgroundCards || `<p class="empty-state">Nenhum antecedente disponível com esta configuração de conteúdo.</p>`}</div>
    </section>
    ${bg ? renderBackgroundDetails(bg) : `<div class="notice-banner">Escolha um antecedente para revelar seus aumentos, proficiências e equipamento de origem.</div>`}
    ${race ? renderSpeciesDetails(race) : `<section class="form-section"><h3>Espécie</h3><p>Volte à primeira etapa e escolha uma espécie para revelar suas linhagens e traços.</p></section>`}`;
}

function renderBackgroundDetails(bg) {
  const options = bg.ability_options || [];
  const selectedMode = state.increaseModeByBackground[bg.key] || "two";
  const picks = state.increasePicksByBackground[bg.key] || [];
  const increasePicks = selectedMode === "two" ? [picks[0] || "", picks[1] || ""] : [picks[0] || "", picks[1] || "", picks[2] || ""];
  const optionsMarkup = `<option value="">Escolha um atributo…</option>` + options.map((item) => `<option value="${esc(item.key)}">${esc(item.label)}</option>`).join("");
  const equipment = bg.equipment || {};
  const equipmentChoices = Object.entries(equipment).map(([key, description]) => `
    <button type="button" class="choice-card ${currentEquipment() === key ? "selected" : ""}" data-choice-field="background_equipment" data-value="${esc(key)}" aria-pressed="${currentEquipment() === key}">
      <strong>Pacote ${esc(key)}</strong><span>${esc(description)}</span>
    </button>`).join("");
  const toolChoice = bg.tool_choice;
  let featChoice = "";
  if (bg.feat_choice) {
    const allDarkGifts = catalog.feats.filter((feat) => feat.category === "dadiva_sombria");
    const optionsList = allDarkGifts.filter((feat) => !feat.requires_ravenloft || state.ravenloft);
    const storedFeat = currentBackgroundFeat();
    const currentDefault = bg.feat.startsWith("dadiva_sombria") ? "" : bg.feat;
    const selectedFeat = storedFeat || currentDefault;
    const choices = [];
    if (currentDefault) choices.push({ key: currentDefault, label: `${thisLabel(bg.feat_label)} · opção do antecedente` });
    for (const feat of optionsList) choices.push({ key: feat.key, label: feat.label });
    featChoice = `
      <div class="field mt-16"><label for="background-feat">Talento do antecedente</label>
        <select id="background-feat" class="select-input" data-field="background_feat"><option value="">Escolha uma dádiva…</option>
          ${choices.map((option) => `<option value="${esc(option.key)}" ${selectedFeat === option.key ? "selected" : ""}>${esc(option.label)}</option>`).join("")}
        </select>
        <small>As Dádivas Sombrias só aparecem com o conteúdo Ravenloft ativo. Efeitos sem suporte serão identificados na revisão.</small>
      </div>`;
  }
  return `
    <section class="form-section">
      <h3>Marcas da origem · ${esc(bg.label)}</h3>
      <p>Proficiências do antecedente: ${(bg.skills || []).map((skill) => esc(skill.label)).join(" e ") || "nenhuma listada"}. Talento: ${esc(bg.feat_label || humanize(bg.feat))}.</p>
      <div class="form-section no-margin">
        <div class="field-label">Aumentos de atributo concedidos pelo antecedente</div>
        <p class="helper">Use +2 em um atributo e +1 em outro, ou +1 em três atributos. As escolhas devem pertencer às opções do antecedente.</p>
        <div class="increment-pattern">
          <button class="segment-button ${selectedMode === "two" ? "selected" : ""}" type="button" data-action="increase-mode" data-value="two">+2 / +1</button>
          <button class="segment-button ${selectedMode === "three" ? "selected" : ""}" type="button" data-action="increase-mode" data-value="three">+1 / +1 / +1</button>
        </div>
        <div class="increase-picks">${increasePicks.map((value, index) => `
          <div class="field"><label for="increase-${index}">${selectedMode === "two" && index === 0 ? "+2 em" : `+1 em`}</label>
            <select id="increase-${index}" class="select-input" data-increase-index="${index}">${optionsMarkup.replace(`value="${esc(value)}"`, `value="${esc(value)}" selected`)}</select>
          </div>`).join("")}</div>
      </div>
      ${toolChoice ? `<div class="field mt-16"><label for="background-tool">${esc(toolChoice.rotulo)}</label><select id="background-tool" class="select-input" data-field="background_tool"><option value="">Escolha uma opção…</option>${toolChoice.opcoes.map((tool) => `<option value="${esc(tool)}" ${currentBackgroundTool() === tool ? "selected" : ""}>${esc(tool)}</option>`).join("")}</select></div>` : `<p class="helper mt-16">Ferramenta do antecedente: ${esc(bg.tool || "não especificada")}</p>`}
      <div class="field mt-16"><div class="field-label">Equipamento de origem</div><p class="helper">Escolha um dos pacotes registrados para este antecedente.</p><div class="choice-grid">${equipmentChoices}</div></div>
      ${featChoice}
      <div class="tag-row mt-16"><span class="source-tag">${esc(bg.source)}</span>${bg.requires_ravenloft ? '<span class="status-tag partial">Ravenloft</span>' : ""}</div>
    </section>`;
}

function thisLabel(value) { return value || "Talento do antecedente"; }

function renderSpeciesDetails(race) {
  const choice = race.choice;
  const current = currentSpeciesChoice();
  const selectedOption = choice?.options?.find((option) => option.key === current);
  const sizeOptions = race.size_options || [];
  const skillChoice = race.skill_choice;
  const currentSkill = currentSpeciesSkill();
  const originFeats = catalog.feats.filter((feat) => feat.category === "origem" && (!feat.requires_ravenloft || state.ravenloft));
  const traits = (race.traits || []).map((trait) => `
    <div class="catalog-card"><h4>${esc(trait.name || "Traço")}</h4><p>${esc(trait.effect || "Descrição não registrada no catálogo.")}</p>
      <div class="tag-row"><span class="tag">Nível ${esc(trait.minimum_level ?? 1)}</span>${trait.resource ? `<span class="tag">${esc(typeof trait.resource === "string" ? trait.resource : JSON.stringify(trait.resource))}</span>` : ""}</div>
    </div>`).join("");
  const choiceBlock = choice ? `
    <div class="field mt-16"><label for="species-choice">${esc(choice.label)}</label>
      <select id="species-choice" class="select-input" data-field="species_choice"><option value="">Escolha uma opção…</option>${choice.options.map((option) => `<option value="${esc(option.key)}" ${current === option.key ? "selected" : ""}>${esc(option.label)}</option>`).join("")}</select>
      ${selectedOption ? `<small>${esc(selectedOption.description || "Opção registrada no catálogo do motor.")}</small>` : ""}
    </div>` : "";
  const sizeBlock = sizeOptions.length > 1 ? `
    <div class="field mt-16"><label for="species-size">Tamanho</label><select id="species-size" class="select-input" data-field="size"><option value="">Escolha um tamanho…</option>${sizeOptions.map((option) => `<option value="${esc(option)}" ${currentSize() === option ? "selected" : ""}>${esc(humanize(option))}</option>`).join("")}</select></div>` : "";
  const skillBlock = skillChoice ? `
    <div class="field mt-16"><label for="species-skill">${esc(skillChoice.label)}</label><select id="species-skill" class="select-input" data-field="species_skill"><option value="">Escolha uma perícia…</option>${skillChoice.options.map((option) => `<option value="${esc(option.key)}" ${currentSkill === option.key ? "selected" : ""}>${esc(option.label)}</option>`).join("")}</select><small>${esc(skillChoice.source_note || "")}</small></div>` : "";
  const humanFeat = state.species === "humano" ? `
    <div class="field mt-16"><label for="species-feat">Talento de Origem adicional · Humano</label>
      <select id="species-feat" class="select-input" data-field="species_feat"><option value="">Escolha um talento…</option>${originFeats.map((feat) => `<option value="${esc(feat.key)}" ${state.speciesFeat === feat.key ? "selected" : ""}>${esc(feat.label)}${feat.requires_spellcasting ? " · exige conjuração" : ""}</option>`).join("")}</select>
      <small>O motor confere categoria, pré-requisitos, talento concedido pelo antecedente e conteúdo Ravenloft.</small>
    </div>` : "";
  return `
    <section class="form-section">
      <div class="panel-header-row"><div><h3>Linhas de ${esc(race.label)}</h3><p class="no-margin">Traços, escolhas e descrições fornecidos pelo Rule Engine.</p></div><span class="source-tag">${esc(race.source)}</span></div>
      ${choiceBlock}${sizeBlock}${skillBlock}${humanFeat}
      ${traits ? `<div class="feature-list mt-16">${traits}</div>` : ""}
    </section>`;
}

function renderAbilityStep() {
  const method = state.abilityMethod;
  const methods = [
    { key: "standard_array", title: "Matriz padrão", description: "15, 14, 13, 12, 10 e 8, cada valor uma vez." },
    { key: "point_buy", title: "Compra por pontos", description: "27 pontos · valores de 8 a 15, conferidos pelo motor." },
  ];
  const methodCards = methods.map((option) => `<button type="button" class="choice-card ${method === option.key ? "selected" : ""}" data-choice-field="ability_method" data-value="${option.key}" aria-pressed="${method === option.key}"><strong>${option.title}</strong><span>${option.description}</span></button>`).join("");
  const standardValues = catalog.score_methods.standard_array.values || [15, 14, 13, 12, 10, 8];
  const scoreRows = ABILITY_ORDER.map((ability) => {
    const value = state.abilityScores[ability] ?? "";
    const input = method === "standard_array"
      ? `<select class="select-input" data-score="${ability}" aria-label="${ABILITY_SKILLS[ability]}"><option value="">—</option>${standardValues.map((score) => `<option value="${score}" ${Number(value) === Number(score) ? "selected" : ""}>${score}</option>`).join("")}</select>`
      : `<input class="number-input" type="number" min="8" max="15" step="1" data-score="${ability}" value="${esc(value)}" aria-label="${ABILITY_SKILLS[ability]}" />`;
    return `<div class="attribute-row"><div class="attribute-name"><strong>${ABILITY_SKILLS[ability]}</strong><small>${ability.toUpperCase()}</small></div>${input}<div class="attribute-final">com origem<strong data-final-ability="${ability}">${state.abilityScores[ability] === "" ? "—" : finalScore(ability)}</strong></div></div>`;
  }).join("");
  const increases = currentIncreases();
  const background = backgroundData();
  const increaseSummary = background ? `<div class="notice-banner mt-16">${esc(background.label)}: ${Object.keys(increases).length ? Object.entries(increases).map(([ability, amount]) => `+${amount} ${ABILITY_SKILLS[ability]}`).join(" · ") : "escolhas de aumento ainda não concluídas"}. Os valores finais respeitam exatamente essas escolhas.</div>` : `<div class="notice-banner mt-16">Escolha um antecedente na etapa anterior para distribuir os aumentos concedidos.</div>`;
  return `
    <section class="form-section"><h3>Como construir os atributos</h3><p>O Rule Engine valida os seis valores. A matriz ou compra representa a pontuação base; os aumentos de origem aparecem separadamente.</p><div class="choice-grid">${methodCards}</div></section>
    <section class="form-section"><div class="panel-header-row"><div><h3>Distribuição base</h3><p class="no-margin">${method === "point_buy" ? "Edite de 8 a 15. O total de pontos será calculado pelo motor." : "Atribua cada valor da matriz a um atributo; valores repetidos não são aceitos."}</p></div><span class="source-tag">Nível 1</span></div>
      <div class="attribute-list mt-16">${scoreRows}</div>
      <div class="point-ledger ${scoreError ? "invalid" : ""}" id="point-ledger"><span data-points-message>${esc(scoreError || "Conferindo a distribuição…")}</span><strong data-points-value>…</strong></div>
      ${increaseSummary}
    </section>`;
}

function renderClassStep() {
  const classes = catalog.classes;
  const cards = classes.map((item) => `
    <button type="button" class="choice-card ${state.class === item.key ? "selected" : ""}" data-choice-field="class" data-value="${esc(item.key)}" aria-pressed="${state.class === item.key}">
      <strong>${esc(item.label)}</strong><span>d${esc(item.hit_die)} · ${esc(item.primary_ability_label || humanize(item.primary_ability))}</span>
      <small>${esc(item.source)}</small>
    </button>`).join("");
  const profile = currentProfile();
  const classInfo = classData();
  if (!classInfo) return `<section class="form-section"><h3>Escolha sua classe</h3><p>A classe determina proficiências, características de nível 1 e progressão. O nível inicial deste fluxo é 1.</p><div class="choice-grid">${cards}</div></section>`;
  return `
    <section class="form-section"><div class="panel-header-row"><div><h3>Escolha sua classe</h3><p class="no-margin">Nível 1 · Dado de Vida d${esc(classInfo.hit_die)} · Atributo primário: ${esc(classInfo.primary_ability_label || humanize(classInfo.primary_ability))}</p></div><span class="source-tag">${esc(classInfo.source)}</span></div><div class="choice-grid three mt-16">${cards}</div></section>
    ${profile ? renderClassProfile(profile, classInfo) : `<div class="notice-banner">Consultando as características de ${esc(classInfo.label)} no Rule Engine…</div>`}
    ${renderClassSkillChoices(classInfo)}
    ${state.class === "artifice" ? renderArtificerWorkshop(profile, classInfo) : ""}
    ${renderClassFeatureChoices(profile)}
    ${renderExpertise(profile)}`;
}

function renderClassProfile(profile, classInfo) {
  const features = profile.features || [];
  const saving = (profile.saving_throws || []).map((key) => humanize(key)).join(" e ");
  const proficiencies = profile.proficiencies || {};
  const profTags = [];
  for (const [group, values] of Object.entries(proficiencies)) {
    if (Array.isArray(values) && values.length) profTags.push(`${humanize(group)}: ${values.join(", ")}`);
  }
  const featuresMarkup = features.map((feature) => {
    const result = feature.result || {};
    const outcome = result.resultado || "resolvido";
    const status = ["nao_implementado", "bloqueado"].includes(outcome) ? "partial" : "";
    const summary = featureSummary(result);
    return `<div class="feature-item"><div><h4>${esc(feature.name)}</h4><p>${esc(summary)}</p></div><span class="feature-status ${status}">${esc(outcomeLabel(outcome))}</span></div>`;
  }).join("");
  const subclassMarkup = (classInfo.subclasses || []).length ? `
    <div class="form-section"><div class="panel-header-row"><div><h3>Subclasses</h3><p class="no-margin">O motor só libera a escolha no nível 3; neste fluxo ela é informativa, não selecionável.</p></div><span class="tag">Nível 3</span></div>
      <div class="choice-grid mt-16">${classInfo.subclasses.map((item) => `<div class="catalog-card"><h4>${esc(item.label)}</h4><p>${item.details_supported ? "O motor possui detalhes de características da subclasse." : "O motor não oferece uma implementação completa dos detalhes desta subclasse."}</p><div class="tag-row"><span class="source-tag">${esc(item.source)}</span><span class="status-tag ${item.details_supported ? "good" : "partial"}">${item.details_supported ? "Detalhes disponíveis" : "Cobertura parcial"}</span></div></div>`).join("")}</div>
    </div>` : "";
  const progression = renderProgression(profile.progression || [], profile.artificer_coverage?.coverage || []);
  return `
    <section class="form-section"><div class="panel-header-row"><div><h3>Ficha de classe · ${esc(profile.class_label)}</h3><p class="no-margin">Proficiências em salvaguardas: ${esc(saving || "conforme registro do motor")}.</p></div><span class="status-tag good">Perfil consultado</span></div>
      ${profTags.length ? `<div class="tag-row mt-16">${profTags.map((tag) => `<span class="tag">${esc(tag)}</span>`).join("")}</div>` : ""}
      <div class="form-section"><h3>Características de nível 1</h3><div class="feature-list mt-12">${featuresMarkup || `<p class="empty-state">Nenhuma característica listada para este nível.</p>`}</div></div>
      ${state.class === "artifice" ? renderArtificerCoverage(profile.artificer_coverage) : ""}
      ${subclassMarkup}
      <details class="form-section progression-details"><summary class="subsection-title">Ver progressão de níveis 1–20</summary><p class="helper">Progressão transcrita do catálogo do Rule Engine; níveis acima do 1º não são simulados nesta criação.</p>${progression}</details>
    </section>`;
}

function renderClassSkillChoices(classInfo) {
  const chosen = currentClassSkills();
  const backgroundSkills = new Set((backgroundData()?.skills || []).map((item) => item.key));
  const speciesSkill = currentSpeciesSkill();
  const disabledSkills = new Set([...backgroundSkills, ...(speciesSkill ? [speciesSkill] : [])]);
  const options = (classInfo.skill_options || []).map((option) => {
    const checked = chosen.includes(option.key);
    const locked = disabledSkills.has(option.key) && !checked;
    const title = locked ? "Já concedida pela origem ou espécie" : "";
    return `<label class="check-card ${checked ? "checked" : ""} ${locked ? "locked" : ""}" title="${esc(title)}"><input type="checkbox" data-field="class-skill" value="${esc(option.key)}" ${checked ? "checked" : ""} ${locked ? "disabled" : ""}><span class="check-box" aria-hidden="true">${checked ? "✓" : ""}</span><span><strong>${esc(option.label)}</strong><small>${locked ? "Já concedida" : "Opção de classe"}</small></span></label>`;
  }).join("");
  return `<section class="form-section"><div class="panel-header-row"><div><h3>Perícias de classe</h3><p class="no-margin">Escolha ${esc(classInfo.skill_count)} dentre as opções da classe, sem duplicar perícias da origem ou espécie.</p></div><span class="tag">${chosen.length} / ${esc(classInfo.skill_count)}</span></div><div class="check-grid mt-16">${options}</div></section>`;
}

function renderClassFeatureChoices(profile) {
  if (!profile) return "";
  const required = (profile.required_choices || []).filter((choice) => choice.key !== "especializacao");
  if (!required.length) return "";
  return `<section class="form-section"><h3>Decisões da classe</h3><p>As opções abaixo são resolvidas pela característica correspondente do motor.</p><div class="field-grid">${required.map((choice) => {
    const selected = classChoices()[choice.key] || "";
    return `<div class="field"><label for="class-choice-${esc(choice.key)}">${esc(choice.label)}</label>
      <select class="select-input" id="class-choice-${esc(choice.key)}" data-class-choice="${esc(choice.key)}"><option value="">Escolha uma opção…</option>${(choice.options || []).map((option) => `<option value="${esc(option.key)}" ${selected === option.key ? "selected" : ""}>${esc(option.label)}</option>`).join("")}</select>
      <small>${selected ? "Opção conferida pelo Rule Engine." : "A decisão fica pendente até selecionar uma opção."}</small>
    </div>`;
  }).join("")}</div></section>`;
}

function renderExpertise(profile) {
  const choice = (profile?.required_choices || []).find((item) => item.key === "especializacao");
  if (!choice) return "";
  const available = new Map();
  for (const skill of backgroundData()?.skills || []) available.set(skill.key, skill.label);
  for (const skill of classSkills()) available.set(skill, STAT_SKILL_LABELS[skill] || humanize(skill));
  const species = speciesData();
  if (species?.skill_choice && currentSpeciesSkill()) available.set(currentSpeciesSkill(), STAT_SKILL_LABELS[currentSpeciesSkill()] || humanize(currentSpeciesSkill()));
  const chosen = expertise();
  const options = [...available.entries()].map(([key, label]) => `<label class="check-card ${chosen.includes(key) ? "checked" : ""}"><input type="checkbox" data-field="expertise" value="${esc(key)}" ${chosen.includes(key) ? "checked" : ""}><span class="check-box" aria-hidden="true">${chosen.includes(key) ? "✓" : ""}</span><span><strong>${esc(label)}</strong><small>Proficiência disponível</small></span></label>`).join("");
  return `<section class="form-section"><h3>Especialização</h3><p>${esc(choice.note || "Escolha entre perícias em que você tem proficiência.")} Selecione ${esc(choice.count)}.</p><div class="check-grid">${options || `<p class="empty-state">Escolha as perícias de classe antes da Especialização.</p>`}</div></section>`;
}

function renderArtificerWorkshop(profile, classInfo) {
  const toolOptions = classInfo.tool_options || [];
  return `<section class="form-section artificer-workshop"><div class="panel-header-row"><div><div class="section-kicker">Oficina do Artífice</div><h3>Ferramentas e limites reais</h3></div><span class="status-tag partial">Implementação parcial</span></div>
    <p>A progressão, as características listadas pelo motor e os helpers de conjuração estão expostos. Infusões, catálogo de itens e validação da escolha de item mágico não estão implementados — não há seleção fictícia nesta tela.</p>
    <div class="field mt-16"><label for="artisan-tool">Proficiência com Ferramentas de Artesão</label><select id="artisan-tool" class="select-input" data-field="artisan_tool_proficiency"><option value="">Escolha uma ferramenta…</option>${toolOptions.map((tool) => `<option value="${esc(tool)}" ${state.artisanToolProficiency === tool ? "selected" : ""}>${esc(tool)}</option>`).join("")}</select><small>A lista vem do conjunto de ferramentas já reconhecido pelo motor.</small></div>
    ${profile?.artificer_coverage ? `<div class="tag-row mt-16"><span class="tag">${esc(profile.artificer_coverage.available_spell_count)} magias no catálogo parcial</span><span class="tag">Fonte de progressão: ${esc(profile.artificer_coverage.spell_progression_source)}</span></div>` : ""}
  </section>`;
}

function renderArtificerCoverage(coverage) {
  if (!coverage) return "";
  const coverageMarkup = (coverage.coverage || []).map((item) => `<div class="feature-item"><div><h4>Nível ${esc(item.level)} · ${esc(item.feature)}</h4><p>${esc(featureSummary(item.result || {}))}</p></div><span class="feature-status ${item.status === "implemented" ? "" : "partial"}">${esc(coverageStatus(item.status))}</span></div>`).join("");
  const castingLevels = (coverage.spell_progression || []).map((item) => `<div class="progression-level"><strong>Nível ${esc(item.nivel)}</strong><span>${esc(item.truques)} truques · ${esc(item.magias_preparadas)} preparadas · até ${esc(item.circulo_maximo)}º círculo · espaços ${esc(JSON.stringify(item.espacos_totais))}</span></div>`).join("");
  const unlinkedTables = (coverage.unlinked_subclass_spell_tables || []).map((subclass) => `<div class="catalog-card"><h4>${esc(subclass.label)} <span class="status-tag partial">Não vinculada</span></h4><p>${(subclass.levels || []).map((level) => `Nível ${esc(level.level)}: ${(level.spells || []).map(esc).join(", ")}`).join(" · ")}</p><div class="tag-row"><span class="source-tag">${esc(subclass.source)}</span></div></div>`).join("");
  return `<div class="form-section artificer-coverage"><h3>Mapa de cobertura do Artífice</h3><p>${esc(coverage.source_note)}</p>
    <details class="form-section"><summary class="subsection-title">Progressão de conjuração · níveis 1–20</summary><p class="helper">Contagens recalculadas pelo helper existente para a Inteligência final deste rascunho.</p><div class="progression-list mt-12">${castingLevels}</div></details>
    <details class="form-section"><summary class="subsection-title">Tabelas de magia de subclasse não vinculadas</summary><p class="helper">${esc(coverage.subclass_note || "Estas tabelas não são escolhas validáveis neste fluxo.")}</p>${unlinkedTables}</details>
    <div class="form-section"><h3>Implementação por característica</h3><div class="feature-list mt-12">${coverageMarkup}</div></div>
    <div class="notice-banner mt-16"><strong>Infusões:</strong> ${esc(coverage.infusion_note)}</div></div>`;
}

function renderProgression(levels, coverage = []) {
  if (!levels.length) return `<p class="empty-state">O motor não registrou dados de progressão para esta classe.</p>`;
  const byLevel = new Map();
  coverage.forEach((item) => byLevel.set(`${item.level}:${item.feature}`, item.status));
  return `<div class="progression-list mt-12">${levels.map((item) => {
    const features = (item.features || []).map((feature) => {
      const status = byLevel.get(`${item.level}:${feature}`);
      return `${esc(feature)}${status === "partial" ? " · cobertura parcial" : status === "unimplemented" ? " · não implementado" : ""}`;
    }).join(" · ");
    return `<div class="progression-level"><strong>Nível ${esc(item.level)}</strong><span>${features}</span></div>`;
  }).join("")}</div>`;
}

function renderMagicStep() {
  const profile = currentProfile();
  const spell = profile?.spellcasting;
  if (!state.class) return `<section class="form-section"><h3>Magia no primeiro nível</h3><p>Escolha uma classe para consultar a característica de conjuração e as listas do motor. A interface não estima quantidades.</p></section>`;
  if (!profile) return `<section class="form-section"><h3>Magia no primeiro nível · ${esc(classData()?.label || humanize(state.class))}</h3><div class="notice-banner">Consultando a característica e as listas de ${esc(classData()?.label || humanize(state.class))} no Rule Engine…</div></section>`;
  if (!spell || !spell.available) return `<section class="form-section"><h3>Magia no primeiro nível · ${esc(classData()?.label || humanize(state.class))}</h3><div class="notice-banner">O Rule Engine não registra escolhas de magia no nível 1 para esta classe. Nenhuma seleção de magia foi presumida.</div>${renderClassFeatureChoices(profile)}</section>`;
  if (!spell.supported) return `<section class="form-section"><div class="panel-header-row"><div><h3>Conjuração · ${esc(classData()?.label || humanize(state.class))}</h3><p class="no-margin">${esc(spell.note || "O motor não informa os limites necessários para validar escolhas.")}</p></div><span class="status-tag partial">Sem seleção simulada</span></div>
    <div class="catalog-card mt-16"><h4>Perfil reconhecido</h4><p>Atributo: ${esc(spell.attribute_label || (spell.attribute ? humanize(spell.attribute) : "não determinado"))} · Espaços: ${esc(JSON.stringify(spell.slots ?? "não registrados"))} · Círculo máximo: ${esc(spell.maximum_circle ?? "não registrado")}.</p></div>
  </section>`;
  const selected = spellSelections();
  const catalogue = spell.catalog || [];
  const maxCircle = Number(spell.maximum_circle || 0);
  const cantripCount = Number(spell.cantrips || 0);
  const spellCount = Number(spell.spells || 0);
  const spellbookCount = spell.spellbook === null || spell.spellbook === undefined ? null : Number(spell.spellbook);
  const countSlots = spell.slots ? JSON.stringify(spell.slots) : "não registrados";
  const cantripOptions = catalogue.filter((item) => Number(item.circle) === 0);
  const firstCircleOptions = catalogue.filter((item) => Number(item.circle) > 0 && Number(item.circle) <= maxCircle);
  return `
    <section class="form-section"><div class="panel-header-row"><div><h3>Conjuração · ${esc(classData()?.label || humanize(state.class))}</h3><p class="no-margin">${esc(spell.source || "Lista consultada no Rule Engine")}</p></div><span class="status-tag good">Limites informados pelo motor</span></div>
      <div class="catalog-card mt-16"><h4>${esc(spell.attribute_label || (spell.attribute ? humanize(spell.attribute) : "Atributo de conjuração"))}</h4><p>${esc(spell.spell_label || "Escolhas de magia")} · ${cantripCount} truques · ${spellCount} magias · espaços ${esc(countSlots)} · até ${maxCircle}º círculo.</p>${spell.note ? `<div class="notice-banner mt-12">${esc(spell.note)}</div>` : ""}</div>
      ${spell.class_key === "artifice" ? `<div class="notice-banner mt-12"><strong>Artífice:</strong> seleção e contagem são validadas pelo helper dedicado do motor; a lista disponível é parcial e sua cobertura é explicitada.</div>` : ""}
      ${spellbookCount !== null ? `<div class="notice-banner mt-12">Mago: escolha ${spellbookCount} magias de 1º círculo para registrar no Livro. As magias preparadas devem ser um subconjunto desse livro.</div>` : ""}
      ${renderSpellPicker("cantrips", "Truques", cantripCount, cantripOptions, selected.cantrips)}
      ${renderSpellPicker("spellbook", "Livro de Magias", spellbookCount, firstCircleOptions, selected.spellbook)}
      ${renderSpellPicker("selected", spellbookCount !== null ? "Magias preparadas" : "Magias escolhidas", spellCount, firstCircleOptions, selected.selected)}
      ${catalogue.length ? `<div class="field mt-16"><label for="spell-search">Buscar no catálogo desta classe</label><input id="spell-search" class="text-input spell-filter" data-text="spell-filter" placeholder="Nome, escola ou descrição…" /><small>O filtro afeta as listas acima. Só são aceitas magias presentes na lista e no círculo indicado pelo motor.</small></div>` : `<div class="notice-banner mt-16">A lista de magias da classe não está disponível neste catálogo. Não é possível registrar escolhas sem uma fonte mecânica.</div>`}
    </section>`;
}

function renderSpellPicker(key, label, count, spells, chosen) {
  if (count === null || count === 0) return "";
  const name = key === "spellbook" ? "spells.spellbook" : `spells.${key}`;
  const group = key === "cantrips" ? "Truques" : "Magias";
  const selection = Array.isArray(chosen) ? chosen : [];
  const selectedSpell = spells.find((spell) => selection.includes(spell.name));
  const optionMarkup = spells.map((spell) => {
    const description = spell.effect ? ` · ${String(spell.effect).slice(0, 120)}` : "";
    const school = spell.school ? ` · ${spell.school}` : "";
    return `<option value="${esc(spell.name)}" ${selection.includes(spell.name) ? "selected" : ""}>${esc(spell.name)} · ${Number(spell.circle) === 0 ? "truque" : `${spell.circle}º círculo`}${esc(school)}${esc(description)}</option>`;
  }).join("");
  return `<div class="spell-group mt-16"><label for="spell-${key}"><span>${esc(label)}</span><small>${selection.length} / ${esc(count)} · ${esc(group)}</small></label>
    <select id="spell-${key}" class="select-input" multiple size="7" data-spell-list="${esc(key)}" aria-label="${esc(label)}">${optionMarkup}</select>
    <div class="spell-count">Selecione exatamente ${esc(count)} opção${Number(count) === 1 ? "" : "ões"}. Use Ctrl ou Command para marcar mais de uma.</div>
    <div class="spell-detail" data-spell-detail="${esc(key)}"><strong>${esc(selectedSpell?.name || "Catálogo de magias")}</strong><p>${esc(selectedSpell?.effect || (selectedSpell ? `Escola: ${selectedSpell.school || "não registrada"}. Círculo ${selectedSpell.circle}.` : "Selecione uma magia para ver a descrição fornecida pelo motor."))}</p></div>
  </div>`;
}

function renderReviewStep() {
  if (createdRecord) return renderCreatedRecord();
  const result = previewResult;
  const missing = result?.missing || [];
  const warningList = result?.warnings || [];
  let characterPreview = "";
  if (result?.ready) characterPreview = renderCharacterSheet(result);
  else if (missing.length) characterPreview = `<section class="form-section"><div class="panel-header-row"><div><h3>Antes de criar</h3><p class="no-margin">O serviço ainda aponta escolhas obrigatórias pendentes.</p></div><span class="status-tag partial">${missing.length} pendente${missing.length === 1 ? "" : "s"}</span></div><ul class="missing-list mt-16">${missing.map((item) => `<li>${esc(item.label)} <span class="muted">· ${esc(item.field)}</span></li>`).join("")}</ul><button class="secondary-button mt-16" type="button" data-action="fix-missing">Ir para a primeira escolha pendente</button></section>`;
  else characterPreview = `<div class="notice-banner">${esc(serviceError || "Conferindo os pré-requisitos com o Rule Engine…")}</div>`;
  return `
    ${result?.error ? `<div class="error-banner">${esc(result.error.message)}</div>` : ""}
    ${characterPreview}
    ${warningList.length ? `<section class="form-section"><h3>Limites e observações do motor</h3><p>Estes avisos não são escondidos; consulte-os antes de confirmar.</p><div class="warning-list">${warningList.map((warning) => `<div class="warning-card"><h4>${esc(warning.title)}</h4><p>${esc(warning.message)}</p></div>`).join("")}</div></section>` : ""}
    <section class="form-section"><div class="toggle-row"><div class="toggle-copy"><strong>Confirmação consciente</strong><span>A ficha só será considerada criada após o serviço confirmar que o registro persistiu. Se houver falha, seu rascunho continua aqui.</span></div><span class="status-tag ${result?.ready ? "good" : "partial"}">${result?.ready ? "Pronta para salvar" : "Ainda não pronta"}</span></div></section>`;
}

function renderCharacterSheet(result) {
  const character = result.character || {};
  const scores = result.score_summary?.final_scores || {};
  const choices = result.choices || {};
  const background = backgroundData(choices.background || state.background);
  const klass = classData(choices.class || character.classe || state.class);
  const species = speciesData(choices.species || character.especie || state.species);
  const skillLabels = (choices.class_skills || []).map((key) => STAT_SKILL_LABELS[key] || humanize(key));
  const featureResults = choices.class_feature_results || [];
  return `<section class="form-section"><div class="panel-header-row"><div><div class="section-kicker">Prévia conferida pelo serviço</div><h3>Ficha de ${esc(character.nome || state.name)}</h3><p class="no-margin">Ainda não criada · nenhuma gravação foi confirmada.</p></div><span class="status-tag ${result.completeness === "complete_within_engine_scope" ? "good" : "partial"}">${result.completeness === "complete_within_engine_scope" ? "Dentro do escopo" : "Cobertura limitada"}</span></div>
    <div class="review-sheet mt-16"><h3>${esc(character.nome || state.name)}</h3><p class="review-subtitle">${esc(klass?.label || humanize(state.class))} nível 1 · ${esc(species?.label || humanize(state.species))} · ${esc(background?.label || humanize(state.background))}</p>
      <div class="review-stat-grid">${ABILITY_ORDER.map((ability) => `<div class="review-stat"><span>${ABILITY_SKILLS[ability].slice(0, 3)}</span><strong>${esc(scores[ability] ?? "—")} (${formatModifier(scores[ability])})</strong></div>`).join("")}</div>
      <div class="review-summary-list"><div><strong>Perícias de classe:</strong> ${esc(skillLabels.join(", ") || "nenhuma registrada")}</div><div><strong>Equipamento de origem:</strong> Pacote ${esc(choices.background_equipment || "—")}</div>${choices.species_choice ? `<div><strong>Escolha de espécie:</strong> ${esc(humanize(choices.species_choice))}</div>` : ""}${choices.species_origin_feat ? `<div><strong>Talento adicional de Humano:</strong> ${esc(humanize(choices.species_origin_feat))}</div>` : ""}${choices.artisan_tool_proficiency ? `<div><strong>Ferramenta de Artífice:</strong> ${esc(choices.artisan_tool_proficiency)}</div>` : ""}</div>
    </div>
    ${featureResults.length ? `<div class="form-section"><h3>Características consultadas</h3><div class="feature-list">${featureResults.map((item) => `<div class="feature-item"><div><h4>${esc(item.name)}</h4><p>${esc(featureSummary(item.result || {}))}</p></div><span class="feature-status">${esc(outcomeLabel(item.result?.resultado || "resolvido"))}</span></div>`).join("")}</div></div>` : ""}
    ${result.validation?.spell_choices ? `<div class="tag-row mt-16"><span class="status-tag ${result.validation.spell_choices.status === "validated" ? "good" : "partial"}">Magias: ${esc(result.validation.spell_choices.status === "validated" ? "validadas" : "fora do validador")}</span><span class="tag">Pontuação ${esc(result.score_summary?.method === "point_buy" ? `${result.score_summary.points_spent}/27` : "matriz padrão")}</span></div>` : ""}
  </section>`;
}

function renderCreatedRecord() {
  const character = createdRecord.character || {};
  const date = createdRecord.created_at ? new Date(createdRecord.created_at).toLocaleString("pt-BR", { dateStyle: "medium", timeStyle: "short" }) : "agora";
  return `<section class="form-section"><div class="confirmation"><div class="section-kicker">Persistência confirmada</div><h3>Ficha criada com sucesso</h3><p><strong>${esc(character.nome || state.name)}</strong> foi gravado no serviço em ${esc(date)}. Esta confirmação só aparece depois do commit no armazenamento.</p><p class="record-id">ID ${esc(createdRecord.id || "")}</p></div>
    ${renderCharacterSheet({ ready: true, character, choices: createdRecord.choices, completeness: createdRecord.completeness, score_summary: createdRecord.score_summary, validation: createdRecord.validation })}
    ${createdRecord.warnings?.length ? `<div class="form-section"><h3>Limites registrados na ficha</h3><div class="warning-list">${createdRecord.warnings.map((warning) => `<div class="warning-card"><h4>${esc(warning.title)}</h4><p>${esc(warning.message)}</p></div>`).join("")}</div></div>` : ""}
  </section>`;
}

function renderLiveSummary() {
  const score = previewResult?.score_summary?.final_scores || null;
  const points = scoreResult && state.abilityMethod === "point_buy" ? `${scoreResult.points_spent}/27` : state.abilityMethod === "standard_array" ? "Matriz padrão" : "Compra por pontos";
  return `<div class="live-ledger">
    <div class="ledger-item"><span>Nome</span><span>${esc(state.name.trim() || "Ainda sem nome")}</span></div>
    <div class="ledger-item"><span>Classe</span><span>${esc(classData()?.label || "A escolher")}</span></div>
    <div class="ledger-item"><span>Espécie</span><span>${esc(speciesData()?.label || "A escolher")}</span></div>
    <div class="ledger-item"><span>Antecedente</span><span>${esc(backgroundData()?.label || "A escolher")}</span></div>
    <div class="ledger-divider"></div>
    <div class="ledger-item"><span>Atributos</span><span>${esc(points)}</span></div>
    <div class="ledger-item"><span>Idioma de interface</span><span>Português</span></div>
    ${score ? `<div class="ledger-divider"></div>${ABILITY_ORDER.map((key) => `<div class="ledger-item"><span>${esc(ABILITY_SKILLS[key])}</span><span>${esc(score[key])} · ${formatModifier(score[key])}</span></div>`).join("")}` : ""}
  </div>`;
}
function renderReadiness() {
  if (createdRecord) return `<div class="readiness ready"><span class="readiness-mark">✓</span><span>Persistência confirmada</span></div>`;
  if (previewResult?.ready) return `<div class="readiness ready"><span class="readiness-mark">✓</span><span>Prévia validada; ainda não salva</span></div>`;
  const count = previewResult?.missing?.length;
  return `<div class="readiness"><span class="readiness-mark">…</span><span>${count ? `${count} escolha${count === 1 ? "" : "s"} pendente${count === 1 ? "" : "s"}` : "Aguardando escolhas"}</span></div>`;
}
function updateLiveSummary() {
  const summary = document.querySelector("#live-summary");
  if (summary) summary.innerHTML = renderLiveSummary();
  const readiness = document.querySelector("#live-readiness");
  if (readiness) readiness.innerHTML = renderReadiness();
  const persistState = document.querySelector("[data-persist-state]");
  if (persistState) persistState.textContent = createdRecord ? "Salvo" : draftStorage === "session" ? "Rascunho da sessão" : draftStorage === "memory" ? "Rascunho temporário" : "Rascunho local";
}
function renderPreviewStatus() {
  const alert = document.querySelector("#service-error");
  if (alert) {
    alert.hidden = !serviceError;
    alert.textContent = serviceError;
  }
  const button = document.querySelector('[data-action="create"]');
  if (button && !isCreating) button.disabled = !previewResult?.ready || !apiOnline || Boolean(createdRecord);
  updateLiveSummary();
}

function formatModifier(score) {
  const value = Number(score);
  if (!Number.isFinite(value)) return "—";
  const mod = Math.floor((value - 10) / 2);
  return mod >= 0 ? `+${mod}` : String(mod);
}
function featureSummary(result) {
  if (!result || !Object.keys(result).length) return "Detalhes mecânicos disponíveis no Rule Engine.";
  if (result.resultado === "nao_implementado") return result.motivo || "O motor identifica esta característica como não implementada.";
  if (result.resultado === "bloqueado") return result.motivo || "O motor bloqueou esta opção.";
  const preferred = ["descricao", "efeito", "beneficio", "recurso", "nota", "motivo"];
  for (const key of preferred) if (typeof result[key] === "string" && result[key].length > 0) return result[key];
  const entries = Object.entries(result).filter(([key, value]) => !["resultado", "classe", "nivel", "fonte", "rule_source", "categoria", "talento", "recurso"].includes(key) && ["string", "number", "boolean"].includes(typeof value));
  if (!entries.length) return `Resultado do motor: ${outcomeLabel(result.resultado || "resolvido")}.`;
  return entries.slice(0, 3).map(([key, value]) => `${humanize(key)}: ${typeof value === "boolean" ? (value ? "sim" : "não") : value}`).join(" · ");
}
function outcomeLabel(value) {
  return ({ resolvido: "Coberto pelo motor", escolha: "Escolha disponível", bloqueado: "Bloqueado pelo motor", nao_implementado: "Não implementado", disponivel: "Disponível" })[value] || humanize(value);
}
function coverageStatus(value) {
  return ({ implemented: "Implementado", partial: "Parcial", unimplemented: "Não implementado" })[value] || humanize(value);
}

function showServiceError(message) {
  serviceError = message;
  const element = document.querySelector("#service-error");
  if (element) { element.hidden = false; element.textContent = message; }
}
function setMainStep(step) {
  currentStep = Math.max(0, Math.min(APP_STEPS.length - 1, step));
  state.step = currentStep;
  saveDraft();
  renderApp();
  if ([3, 4, 5].includes(currentStep)) schedulePreview({ immediate: true });
  if (currentStep === 2) scheduleScorePreview({ immediate: true });
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function updateClassSkill(value, checked) {
  const list = [...currentClassSkills()];
  state.classSkillsByClass[state.class] = checked ? [...new Set([...list, value])] : list.filter((item) => item !== value);
}
function updateExpertise(value, checked) {
  const list = [...expertise()];
  state.expertiseByClass[state.class] = checked ? [...new Set([...list, value])] : list.filter((item) => item !== value);
}
function selectedValues(select) { return Array.from(select.selectedOptions).map((option) => option.value); }
function updateSpellPicker(select) {
  const key = select.dataset.spellList;
  const picks = selectedValues(select);
  const label = select.parentElement.querySelector("label small");
  if (label) {
    const limit = label.textContent.split("/").pop()?.split("·")[0]?.trim() || "?";
    label.textContent = `${picks.length} / ${limit} · ${key === "cantrips" ? "Truques" : "Magias"}`;
  }
  const detail = select.parentElement.querySelector(`[data-spell-detail="${key}"]`);
  if (detail) {
    const spell = (currentProfile()?.spellcasting?.catalog || []).find((item) => item.name === picks[0]);
    const heading = detail.querySelector("strong");
    const description = detail.querySelector("p");
    if (heading) heading.textContent = spell?.name || "Catálogo de magias";
    if (description) description.textContent = spell?.effect || (spell ? `Escola: ${spell.school || "não registrada"}. Círculo ${spell.circle}.` : "Selecione uma magia para ver a descrição fornecida pelo motor.");
  }
}

function onAppInput(event) {
  const target = event.target;
  if (target.matches("[data-text]")) {
    const key = target.dataset.text;
    if (key === "appearance" || key === "backstory" || key === "motive") state.narrative[key] = target.value;
    else if (key === "spell-filter") { filterSpellOptions(target.value); return; }
    else state[key] = target.value;
    saveDraft();
    updateLiveSummary();
    schedulePreview();
  }
  if (target.matches("[data-score]")) {
    state.abilityScores[target.dataset.score] = target.value === "" ? "" : Number(target.value);
    scoreResult = null;
    scoreError = "";
    saveDraft();
    updateScoreLedger();
    scheduleScorePreview();
    schedulePreview();
    refreshAttributeFinals();
  }
}

function onAppChange(event) {
  const target = event.target;
  if (target.matches("[data-score]")) {
    state.abilityScores[target.dataset.score] = target.value === "" ? "" : Number(target.value);
    saveDraft();
    scheduleScorePreview({ immediate: true });
    schedulePreview({ immediate: true });
    renderApp();
    return;
  }
  if (target.matches("[data-field='ravenloft']")) {
    state.ravenloft = target.checked;
    if (!state.ravenloft) {
      if (backgroundData()?.requires_ravenloft) state.background = "";
      const selectedBackgroundFeat = currentBackgroundFeat();
      if (catalog.feats.some((feat) => feat.key === selectedBackgroundFeat && feat.requires_ravenloft)) state.backgroundFeatByBackground[state.background] = "";
      if (catalog.feats.some((feat) => feat.key === state.speciesFeat && feat.requires_ravenloft)) state.speciesFeat = "";
    }
    createdRecord = null;
    saveDraft(); renderApp(); schedulePreview({ immediate: true }); return;
  }
  if (target.matches("[data-field='background_feat']")) state.backgroundFeatByBackground[state.background] = target.value;
  else if (target.matches("[data-field='background_tool']")) state.toolByBackground[state.background] = target.value;
  else if (target.matches("[data-field='background_equipment']")) state.equipmentByBackground[state.background] = target.value;
  else if (target.matches("[data-field='species_choice']")) state.speciesChoiceBySpecies[state.species] = target.value;
  else if (target.matches("[data-field='species_skill']")) state.speciesSkillBySpecies[state.species] = target.value;
  else if (target.matches("[data-field='size']")) state.sizeBySpecies[state.species] = target.value;
  else if (target.matches("[data-field='species_feat']")) state.speciesFeat = target.value;
  else if (target.matches("[data-field='artisan_tool_proficiency']")) state.artisanToolProficiency = target.value;
  else if (target.matches("[data-field='class-skill']")) updateClassSkill(target.value, target.checked);
  else if (target.matches("[data-field='expertise']")) updateExpertise(target.value, target.checked);
  else if (target.matches("[data-class-choice]")) classChoices()[target.dataset.classChoice] = target.value;
  else if (target.matches("[data-spell-list]")) {
    const key = target.dataset.spellList;
    const field = key === "spellbook" ? "spellbook" : key;
    spellSelections()[field] = selectedValues(target);
  } else if (target.matches("[data-field='ability_method']")) state.abilityMethod = target.value;
  else if (target.matches("[data-increase-index]")) {
    const background = state.background;
    const picks = [...(state.increasePicksByBackground[background] || [])];
    picks[Number(target.dataset.increaseIndex)] = target.value;
    state.increasePicksByBackground[background] = picks;
  }
  if (target.matches("[data-spell-list]")) {
    createdRecord = null;
    saveDraft();
    updateSpellPicker(target);
    schedulePreview();
    return;
  }
  if (target.matches("[data-field='background_feat'], [data-field='background_tool'], [data-field='background_equipment'], [data-field='species_choice'], [data-field='species_skill'], [data-field='size'], [data-field='species_feat'], [data-field='artisan_tool_proficiency'], [data-field='ability_method'], [data-increase-index], [data-class-choice], [data-field='class-skill'], [data-field='expertise']")) {
    createdRecord = null;
    saveDraft();
    renderApp();
    schedulePreview({ immediate: true });
    if (currentStep === 2) scheduleScorePreview({ immediate: true });
  }
}

function onAppClick(event) {
  const stepButton = event.target.closest("[data-step]");
  if (stepButton) { setMainStep(Number(stepButton.dataset.step)); return; }
  const choice = event.target.closest("[data-choice-field]");
  if (choice) {
    const field = choice.dataset.choiceField;
    const value = choice.dataset.value;
    if (field === "species") {
      state.species = value;
    } else if (field === "background") {
      state.background = value;
      if (!state.increaseModeByBackground[value]) state.increaseModeByBackground[value] = "two";
    } else if (field === "class") {
      state.class = value;
      if (!state.classSkillsByClass[value]) state.classSkillsByClass[value] = [];
      if (!state.classChoicesByClass[value]) state.classChoicesByClass[value] = {};
      if (!state.spellsByClass[value]) state.spellsByClass[value] = { cantrips: [], selected: [], spellbook: [] };
      state.expertiseByClass[value] ||= [];
    } else if (field === "ability_method") {
      state.abilityMethod = value;
    } else if (field === "background_equipment") {
      state.equipmentByBackground[state.background] = value;
    }
    createdRecord = null;
    saveDraft();
    renderApp();
    schedulePreview({ immediate: true });
    if (field === "ability_method") scheduleScorePreview({ immediate: true });
    return;
  }
  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) return;
  const action = actionButton.dataset.action;
  if (action === "previous") setMainStep(currentStep - 1);
  if (action === "next") setMainStep(currentStep + 1);
  if (action === "increase-mode") {
    const background = state.background;
    state.increaseModeByBackground[background] = actionButton.dataset.value;
    state.increasePicksByBackground[background] = [];
    saveDraft(); renderApp(); schedulePreview({ immediate: true });
  }
  if (action === "create") createCharacter();
  if (action === "fix-missing") goToFirstMissing();
  if (action === "saved-list") openSavedModal();
  if (action === "close-saved") closeSavedModal();
  if (action === "new-draft") startNewDraft();
  if (action === "open-record") openSavedRecord(actionButton.dataset.id);
  if (action === "retry") { schedulePreview({ immediate: true }); scheduleScorePreview({ immediate: true }); }
}

function onDocumentKeydown(event) { if (event.key === "Escape" && modalOpen) closeSavedModal(); }
function refreshAttributeFinals() {
  const background = backgroundData();
  const increases = background ? currentIncreases() : {};
  for (const element of document.querySelectorAll("[data-final-ability]")) {
    const ability = element.dataset.finalAbility;
    element.textContent = state.abilityScores[ability] === "" ? "—" : String(Number(state.abilityScores[ability] || 0) + Number(increases[ability] || 0));
  }
}
function filterSpellOptions(query) {
  const value = normalize(query);
  for (const option of document.querySelectorAll("[data-spell-list] option")) {
    const haystack = normalize(`${option.value} ${option.textContent}`);
    option.hidden = Boolean(value && !haystack.includes(value));
  }
}

function goToFirstMissing() {
  const missing = previewResult?.missing || [];
  if (!missing.length) return;
  const first = missing[0].field;
  let step = 0;
  if (["background", "background_increases", "background_tool", "background_equipment", "background_feat", "species_choice", "species_skill", "size", "species_feat", "ravenloft"].includes(first)) step = 1;
  else if (["ability_scores", "ability_method"].includes(first)) step = 2;
  else if (first.startsWith("class_choices.") || ["class_skills", "expertise", "artisan_tool_proficiency"].includes(first)) step = 3;
  else if (first.startsWith("spells")) step = 4;
  setMainStep(step);
}

async function createCharacter() {
  if (isCreating || !previewResult?.ready || !apiOnline) return;
  isCreating = true;
  renderMainPanel();
  try {
    const result = await requestJSON("/api/characters", { method: "POST", body: JSON.stringify(payloadFromState()) });
    createdRecord = result;
    serviceError = "";
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
    try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
    state.name = result.character?.nome || state.name;
    renderApp();
    await refreshSavedCharacters();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (error) {
    showServiceError(error.message || "A ficha não foi salva. Suas escolhas permanecem no rascunho.");
    updateConnection(error.status !== undefined, error.message);
  } finally {
    isCreating = false;
    renderMainPanel();
  }
}

function startNewDraft() {
  const assignment = catalog.score_methods.standard_array.assignment;
  state = emptyDraft(assignment);
  currentStep = 0;
  previewResult = null;
  scoreResult = null;
  scoreError = "";
  createdRecord = null;
  serviceError = "";
  saveDraft();
  renderApp();
  schedulePreview({ immediate: true });
  scheduleScorePreview({ immediate: true });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function openSavedModal() {
  modalOpen = true;
  renderSavedModal();
  refreshSavedCharacters();
}
function closeSavedModal() { modalOpen = false; renderApp(); }
function renderSavedModal() {
  const root = document.querySelector("#saved-modal-root");
  if (!root) return;
  root.innerHTML = `<div class="modal-backdrop" role="presentation"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="saved-title" data-modal-inner>
    <div class="modal-header"><div><div class="section-kicker">Armazenamento confirmado</div><h2 id="saved-title">Minhas fichas</h2></div><button type="button" class="close-button" data-action="close-saved" aria-label="Fechar">×</button></div>
    ${savedCharacters.length ? `<div class="saved-list">${savedCharacters.map((item) => `<article class="saved-character"><div><strong>${esc(item.name)}</strong><span>${esc(humanize(item.character?.classe || ""))} · ${esc(humanize(item.character?.especie || ""))} · ${formatDate(item.created_at)}</span></div><button type="button" data-action="open-record" data-id="${esc(item.id)}">Ver ficha</button></article>`).join("")}</div>` : `<p class="empty-state">Ainda não há fichas persistidas. Um rascunho só aparece aqui depois que o serviço confirma o salvamento.</p>`}
  </section></div>`;
}
function openSavedRecord(id) {
  const item = savedCharacters.find((record) => record.id === id);
  if (!item) return;
  createdRecord = item;
  currentStep = 5;
  modalOpen = false;
  renderApp();
  requestJSON(`/api/characters/${encodeURIComponent(id)}`).then((record) => { createdRecord = record; renderApp(); }).catch((error) => showServiceError(error.message));
}
function formatDate(value) {
  if (!value) return "data não informada";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "data não informada" : date.toLocaleDateString("pt-BR", { dateStyle: "medium" });
}

appRoot.addEventListener("input", onAppInput);
appRoot.addEventListener("change", onAppChange);
appRoot.addEventListener("click", onAppClick);
document.addEventListener("keydown", onDocumentKeydown);
appRoot.addEventListener("click", (event) => {
  const backdrop = event.target.closest(".modal-backdrop");
  if (backdrop && !event.target.closest("[data-modal-inner]")) closeSavedModal();
});

async function boot() {
  try {
    const [health, rules] = await Promise.all([requestJSON("/api/health"), requestJSON("/api/catalog")]);
    catalog = rules;
    state = loadDraft();
    currentStep = state.step || 0;
    apiOnline = Boolean(health.ok);
    updateConnection(true);
    renderApp();
    schedulePreview({ immediate: true });
    scheduleScorePreview({ immediate: true });
    refreshSavedCharacters();
  } catch (error) {
    updateConnection(false, error.message || "O serviço de regras não respondeu.");
    appRoot.innerHTML = `<div class="app-shell"><header class="topbar"><div class="brand"><div class="brand-mark">✦</div><div class="brand-copy"><strong>Ateliê de Heróis</strong><span>D&amp;D · Edição 2024</span></div></div></header><section class="hero-banner"><div class="hero-copy"><div class="eyebrow">Ateliê temporariamente fechado</div><h1>As regras não responderam.</h1><p>Não iniciamos a criação sem os catálogos e validadores do Rule Engine. Atualize a página para tentar novamente.</p></div></section><div class="error-banner">${esc(error.message || "Falha de comunicação com o serviço.")}</div><button class="primary-button" type="button" data-reload>⟳ Tentar novamente</button></div>`;
    appRoot.addEventListener("click", (event) => { if (event.target.closest("[data-reload]")) window.location.reload(); });
  }
}

boot();
