(() => {
  const options = document.getElementById("action-options");
  const hint = document.getElementById("map-hint");
  const map = document.getElementById("map-scene");
  const labels = {
    move: { title: "MOVIMENTO", items: [{label:"Mostrar casas alcançáveis", grid:true},{label:"Cancelar movimento"}], hint:"Prévia: áreas de movimento destacadas" },
    attack: { title: "ATAQUES", items: [{label:"Ataque com arma", grid:false},{label:"Goblin · alvo de exemplo", grid:true}], hint:"Prévia: selecione um alvo no mapa" },
    spells: { title: "MAGIAS", items: [{label:"Mísseis Mágicos · 1º círculo"},{label:"Outra magia · indisponível", disabled:true}], hint:"Prévia de opções — ainda sem validação do Rule Engine" },
    cantrips: { title: "TRUQUES", items: [{label:"Raio de Fogo"},{label:"Outro truque"}], hint:"Prévia de truques conhecidos" },
    items: { title: "ITENS", items: [{label:"Poção de Cura"},{label:"Mochila"}], hint:"Prévia do inventário" },
    end: { title: "TURNO", items: [{label:"Encerrar turno de demonstração"}], hint:"A prévia não altera a sessão de combate" }
  };
  function choose(action) {
    const config = labels[action];
    document.querySelectorAll(".action-button").forEach(button => button.classList.toggle("active", button.dataset.action === action));
    map.classList.toggle("show-grid", action === "move" || action === "attack");
    hint.textContent = config.hint;
    options.replaceChildren();
    const title = document.createElement("span");
    title.className = "options-label";
    title.textContent = config.title;
    options.append(title);
    const list = document.createElement("div");
    list.className = "option-list";
    config.items.forEach(item => {
      const button = document.createElement("button");
      button.className = "option-button";
      button.textContent = item.label;
      button.disabled = Boolean(item.disabled);
      button.addEventListener("click", () => {
        list.querySelectorAll("button").forEach(other => other.classList.toggle("selected", other === button));
        if (item.grid) map.classList.add("show-grid");
        hint.textContent = item.disabled ? "Esta opção está indisponível nesta demonstração." : item.label + " — prévia visual";
      });
      list.append(button);
    });
    options.append(list);
  }
  document.querySelectorAll(".action-button").forEach(button => button.addEventListener("click", () => choose(button.dataset.action)));
  document.querySelectorAll(".unit").forEach(unit => unit.addEventListener("click", () => {
    hint.textContent = unit.dataset.unit === "hero" ? "Aventureiro selecionado (dado ilustrativo)" : "Goblin selecionado (dado ilustrativo)";
    document.querySelectorAll(".unit").forEach(other => other.style.transform = other === unit ? "scale(1.12)" : "scale(1)");
  }));
})();
