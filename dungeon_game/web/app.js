// Interface do encontro: desenha o estado recebido do servidor e envia pedidos.
// Nenhuma regra é calculada aqui; alcance e alvos vêm da API e são revalidados no backend.

const TAMANHO = 32; // pixels por casa; sprites de inimigos em 16×16 (2px por pixel), heróis em 32×32 nativo
const PIXEL = TAMANHO / 16;

const SPRITES = {
  heroi: {
    pal: {
      o: "#141016",
      h: "#2b2440",
      s: "#e0b48a",
      b: "#4a6fa5",
      B: "#6d95cf",
      g: "#e0b34c",
      w: "#dce6f2",
    },
    linhas: [
      "....oooooooo....",
      "...ohhhhhhhho...",
      "..ohhhhhhhhhho..",
      "..ohssoooossho..",
      "..ohssssssssho..",
      "...oossssssoo..o",
      "..oobBBBBBBbooow",
      ".obbBbbbbbbBbbow",
      ".obbobggggbobbo.",
      "..ooobbbbbboooo.",
      "....obbbbbbo....",
      "....oobbbboo....",
      "....obbo.obbo...",
      "....oboo.oobo...",
      "...oobo...oboo..",
      "...oooo...oooo..",
    ],
  },
  goblin: {
    pal: {
      o: "#141016",
      g: "#62a84f",
      G: "#84cc6c",
      s: "#3e7032",
      e: "#ff3b3b",
      y: "#ffe066",
      l: "#6e4a2e",
      d: "#472f1d",
      w: "#d6e0eb",
      W: "#8b9bb0",
    },
    linhas: [
      "....oooooooo....",
      "..oogGGGGGGgoo..",
      "oogggggGGGGgggoo",
      "ossggeeGGeeggsso",
      ".oooggggggggooo.",
      "...oosggggsoo..o",
      "...oolllllloo.ow",
      "..oggllllllggowW",
      "..ogollddllogow.",
      "..ooolyyyyylooo.",
      "....olllllllo...",
      "....oodddddoo...",
      "....oddo.oddo...",
      "....odoo.oodo...",
      "...oodo...odoo..",
      "...oooo...oooo..",
    ],
  },
  goblin_arqueiro: {
    pal: {
      o: "#141016",
      g: "#62a84f",
      G: "#84cc6c",
      s: "#3e7032",
      e: "#ff3b3b",
      l: "#5c4028",
      d: "#3b2818",
      r: "#c93b3b",
      b: "#d49b54",
      B: "#8c5e2a",
      c: "#e6e1d6",
    },
    linhas: [
      "...oorroooooo...",
      "..oorGGGGGGgoo..",
      "oogggggGGGGgggoo",
      "ossggeeGGeeggsso",
      ".oooggggggggooo.",
      "...oosggggsoo...",
      "..ooolllllloobB.",
      ".oggllllllllgc.b",
      ".ogollddddllgc.b",
      "..ooolllllllgc.b",
      "....ollllllloobB",
      "....oodddddoo...",
      "....oddo.oddo...",
      "....odoo.oodo...",
      "...oodo...odoo..",
      "...oooo...oooo..",
    ],
  },
  esqueleto: {
    pal: {
      o: "#141016",
      b: "#e8e4d6",
      B: "#ffffff",
      s: "#aba494",
      r: "#d92b2b",
      m: "#7a2024",
      w: "#dce6f2",
      W: "#8a99ad",
    },
    linhas: [
      "....oooooooo....",
      "...obBBBBBBbo...",
      "..obBBBBBBBBbo..",
      "..oborboobrobo..",
      "..obbbboobbbbo..",
      "...oosbboobsoo.o",
      "...oobsoosboo.ow",
      "..obobsoosbobowW",
      "..oboosbbsooobw.",
      "...oo.obbo.oooo.",
      ".....obmmbo.....",
      "....oobmmboo....",
      "....obo..obo....",
      "....obo..obo....",
      "...oobo..oboo...",
      "...oooo..oooo...",
    ],
  },
  zumbi: {
    pal: {
      o: "#141016",
      z: "#6b8756",
      Z: "#8ca874",
      s: "#475c38",
      e: "#d93232",
      y: "#e8d26f",
      r: "#9e3333",
      t: "#57412f",
      d: "#38291d",
    },
    linhas: [
      "....oooooooo....",
      "...ozZZZZZZzo...",
      "..ozzzZZZZrzzoo.",
      "..ozzezzzzoeyzo.",
      "..ozzzzzrrzzzzo.",
      ".oooszzzzzzzsoo.",
      "ozzzottttttozzzo",
      "ozssottrtttoszzo",
      ".oooottttttoooo.",
      "....otdtddto....",
      "....oddddddo....",
      "....oddo.oddo...",
      "....odso.ozdo...",
      "....odoo.oodo...",
      "...oodo...odoo..",
      "...oooo...oooo..",
    ],
  },
  cultista: {
    pal: {
      o: "#120d17",
      c: "#591d3d",
      C: "#7d2b57",
      d: "#381026",
      g: "#e0b34c",
      s: "#d9bfa6",
      e: "#ff5252",
      w: "#e2ebf5",
      W: "#8b9bb0",
    },
    linhas: [
      "......oooo......",
      "....oocCCcoo....",
      "...ocCCCCCCco...",
      "..ocCCooooCCco..",
      "..ocCoseesoCco..",
      "..ocddssssddco.o",
      "...oocggggcoo.ow",
      "..occcgddgcccowW",
      ".ocCccgddgccCcow",
      ".ocdoocggcoodco.",
      "..oo.ocCCco.oo..",
      "....occgddcco...",
      "....ocdddddco...",
      "...oocdd.ddcoo..",
      "...oodd...ddoo..",
      "...oooo...oooo..",
    ],
  },
  bandido: {
    pal: {
      o: "#141016",
      h: "#3b2f28",
      H: "#54443a",
      r: "#ba2929",
      R: "#e04848",
      s: "#dfb188",
      b: "#735035",
      d: "#473120",
      g: "#e0b34c",
      w: "#dce6f2",
      W: "#8b9bb0",
    },
    linhas: [
      "....oooooooo....",
      "...ohHHHHHHho...",
      "..ohHHHHHHHHho..",
      "..ohssoooossho..",
      "..ohrrrrrrrrho..",
      "...orRRRRRRro...",
      "..oobbbbbbbboo.o",
      ".obbddbbbbddbbow",
      ".obbdgbbbbgdbbWW",
      "..ooobggggboooo.",
      "....obddddbo....",
      "....ooddddoo....",
      "....oddo.oddo...",
      "....odho.ohdo...",
      "...oodo...odoo..",
      "...oooo...oooo..",
    ],
  },
  orc: {
    pal: {
      o: "#121710",
      g: "#4c803a",
      G: "#6ba655",
      s: "#325725",
      e: "#ff3333",
      t: "#f5f0e1",
      b: "#5e412a",
      d: "#3b2819",
      w: "#dce6f2",
      W: "#8596ab",
      a: "#734f32",
    },
    linhas: [
      "....oooooooo....",
      "...ogGGGGGGgo...",
      "..oggGGGGGGggo.o",
      "..oggeeGGeeggoow",
      "..oggtgoogtggowW",
      "..oosttttttsowWa",
      ".oWgobbbbbbogwW.",
      "oWWgobdbbbdbogao",
      ".ooogbbbbbbbgoao",
      "...oobdtttdbooao",
      "....obdddddbo.o.",
      "....oodddddoo...",
      "....oggo.oggo...",
      "...oogso.osgoo..",
      "...oodo...odoo..",
      "...oooo...oooo..",
    ],
  },
  sombra: {
    pal: {
      o: "#09070d",
      s: "#161121",
      v: "#2d2245",
      V: "#49386e",
      e: "#70e8ff",
      w: "#c2f4ff",
    },
    linhas: [
      "....oooooooo....",
      "...osvVVVVvso...",
      "..osvVVVVVVvso..",
      "..osVewvvwVeso..",
      ".osvVVvvvvVVvso.",
      "osvvssssssssvvso",
      "osvssvVVVVvssvso",
      ".ooosvVVVVvsooo.",
      "...osvvssvvso...",
      "..osvvssssvvso..",
      "..osvsoooosvso..",
      ".osvo..oo..ovso.",
      ".oso...oo...oso.",
      "..o....oo....o..",
      ".......oo.......",
      "................",
    ],
  },
  carnical: {
    pal: {
      o: "#130f1a",
      g: "#8b7f99",
      G: "#afa3bd",
      s: "#5d5369",
      e: "#ff2e2e",
      f: "#f7f3eb",
      r: "#b82525",
      d: "#362b40",
    },
    linhas: [
      "....oooooooo....",
      "...ogGGGGGGgo...",
      "..oggGGGGGGggo..",
      "..oggeeGGeeggo..",
      "..oggsffffsggo..",
      ".ooosfrffrfsooo.",
      "oggooddddddooggo",
      "ogssodsgssdossgo",
      "ofrooddddddoofr.",
      ".oo..oddddo..oo.",
      "....ooddddoo....",
      "...oggsoosggo...",
      "...ogso..osgo...",
      "...ogoo..oogo...",
      "..oofo....ofoo..",
      "..oooo....oooo..",
    ],
  },
  armadura_animada: {
    pal: {
      o: "#10151c",
      l: "#dce7f2",
      m: "#97a8ba",
      d: "#566475",
      g: "#e0b34c",
      e: "#45d4ff",
    },
    linhas: [
      ".....ooggoo.....",
      "...oomllllmoo...",
      "..omllllllllmo..",
      "..omdoooooodmo..",
      "..omdeeeeeedmo..",
      "...oodmmmmddo...",
      ".ooggmllllmggoo.",
      "omllgmllllmgllmo",
      "omddgmggggmgddmo",
      ".ooommddddmmmoo.",
      "....omggggmo....",
      "....omddddmo....",
      "....ommoommo....",
      "...oomd..dmoo...",
      "...oodd..ddoo...",
      "...oooo..oooo...",
    ],
  },
  aparicao: {
    pal: {
      o: "#100c18",
      g: "#ebbd49",
      h: "#282038",
      H: "#3f3357",
      s: "#cad6de",
      e: "#52f2ff",
      r: "#8c1d28",
      R: "#bd2b39",
      w: "#e4effa",
      W: "#8fa3ba",
    },
    linhas: [
      "..o.oog..goo.o..",
      "..ooggggggggoo..",
      "..ohHHHHHHHHho..",
      "..ohssoooossho.o",
      "..ohseessoesshow",
      "..oohsssssshoowW",
      ".orRhhggggghhRwo",
      "orRRhHhhhhHhRRwo",
      "orRrohggggghoRro",
      "orooohHHHHHhooo.",
      ".o..ohrrrrrho...",
      "....ohhhhhhho...",
      "...oohho.ohhoo..",
      "...ohho...ohho..",
      "..ooho.....ohoo.",
      "..oooo.....oooo.",
    ],
  },
  espectro: {
    pal: {
      o: "#07141c",
      c: "#1c4a61",
      C: "#3885a6",
      L: "#7be3ff",
      e: "#ffffff",
      g: "#4bd1f5",
    },
    linhas: [
      "....oooooooo....",
      "...ocCCCCCCco...",
      "..ocCLLLLLLCco..",
      "..ocLeooooelco..",
      "..ocCLLLLLLCco..",
      ".oocCCccccCCcoo.",
      "ocCCcCLLLLCcCCco",
      "ocCLcCCCCCCcLCco",
      ".oocccCLLCCCcco.",
      "...oocCCCCCCoo..",
      "..ocCccccccCco..",
      "..occcoo..occco.",
      ".occo.o....occo.",
      ".oco........oco.",
      "..o..........o..",
      "................",
    ],
  },
  esqueleto_minotauro: {
    pal: {
      o: "#171412",
      b: "#f0ead8",
      s: "#bfb59b",
      h: "#d9c398",
      e: "#ff3b2e",
      a: "#8293a6",
      A: "#dce6f2",
      w: "#6b472a",
    },
    linhas: [
      ".oo..........oo.",
      "ohho..oooo..ohho",
      "ohhhoobbbboohhho",
      ".ooobbssssbbooo.",
      "...obbeebbebo.oA",
      "...obssssssbooaA",
      "..oobbbbbbbbooaw",
      ".obsbboooobbsbow",
      ".obsbboooobbsbow",
      "..ooobssssboooow",
      "....obbbbbbo..o.",
      "...oobbbbbboo...",
      "...obsboobsbo...",
      "...obso..osbo...",
      "..ooboo..ooboo..",
      "..oooo....oooo..",
    ],
  },
  mumia: {
    pal: {
      o: "#1a140e",
      b: "#dfd2b5",
      d: "#ab9a76",
      g: "#f2c14e",
      G: "#b88728",
      r: "#289976",
      e: "#47ff9c",
    },
    linhas: [
      "...ooggggggoo...",
      "..ogGrggggGrgo..",
      "..ogGGGGGGGGgo..",
      "..obddddddddbo..",
      "..obdeeddeedbo..",
      "...obbbbbbbbo...",
      ".ooggbddddbggoo.",
      "obddgbddddbgddbo",
      "obbbgbbbbbbgbbbo",
      "obdoobddddboodbo",
      ".oo.obbbbbbo.oo.",
      "....obddddbo....",
      "....obboobbo....",
      "...oobd..dboo...",
      "...oodb..bdoo...",
      "...oooo..oooo...",
    ],
  },
};

const ICONES_CLASSE = {
  bardo: "🎵",
  monge: "🥋",
  guerreiro: "🛡️",
  barbaro: "🪓",
  ladino: "🗡️",
  clerigo: "✨",
  mago: "🧙",
  paladino: "⚔️",
  druida: "🌿",
  artifice: "🧑‍🔧",
  guardiao: "🏹",
  feiticeiro: "🔥",
  bruxo: "👁️",
};

const ICONES_INIMIGO = {
  goblin: "👺",
  goblin_arqueiro: "🏹",
  esqueleto: "💀",
  zumbi: "🧟",
  cultista: "🗡️",
  bandido: "🥷",
  orc: "👹",
  sombra: "👤",
  carnical: "🩸",
  armadura_animada: "🛡️",
  aparicao: "👑",
  espectro: "👻",
  esqueleto_minotauro: "🐂",
  mumia: "⚱️",
};

const CLASSE_ICONE_MAGIA = {
  "Zombaria Perversa": "spell-musica",
  "Raio de Fogo": "spell-fogo",
  "Toque Chocante": "spell-raio",
  "Raio de Gelo": "spell-gelo",
  "Rajada de Veneno": "spell-veneno",
  "Chicote de Espinhos": "spell-espinhos",
  "Curar Ferimentos": "spell-cura",
  "Palavra Curativa": "spell-cura",
  "Comando": "spell-encanto",
  "Escudo da Fé": "spell-escudo",
  "Escudo Arcano": "spell-escudo",
  "Mísseis Mágicos": "spell-misseis",
  "Armadura Arcana": "spell-armadura",
  "Vitalidade Vazia": "spell-bencao",
  "Marca do Predador": "spell-espinhos",
  "Raio Místico": "spell-misseis",
  "Raio de Bruxa": "spell-raio",
  "Armadura de Agathys": "spell-gelo",
};

const ESTILO_TERRENO = {
  chao: { base: "#2d2930", sombra: "#252128", vinho: "#38323b" },
  parede: { base: "#16131a", sombra: "#1e1a24", vinho: "#2c2430" },
  porta: { base: "#6b4a2a", sombra: "#553a20", vinho: "#8c6538" },
  agua: { base: "#1c4366", sombra: "#163654", vinho: "#295c8a" },
  pilar: { base: "#433c46", sombra: "#322c36", vinho: "#625666" },
  tocha: { base: "#2d2930", sombra: "#252128", vinho: "#38323b" },
};

// Cada arena tem uma paleta própria, sem alterar colisões ou regras táticas.
const TEMAS_MAPA = {
  "cripta-inicial": { piso: "#30333b", sombra: "#242832", acento: "#86b7d8" },
  "santuario-circular": { piso: "#34313a", sombra: "#29232f", acento: "#e0b45e" },
  "catacumba-dos-mortos": { piso: "#2b3431", sombra: "#202a27", acento: "#91b9a0" },
  "camara-profana": { piso: "#38282f", sombra: "#2a1e25", acento: "#d87983" },
  "sarcofago-do-rei-mumia": { piso: "#3a3026", sombra: "#2a221c", acento: "#c7a0df" },
};

function temaMapaAtual() {
  return TEMAS_MAPA[estado.dados?.mapa?.id] || TEMAS_MAPA["cripta-inicial"];
}

const COMANDOS = [
  ["aproximar", "Aproximar"],
  ["largar", "Largar"],
  ["fugir", "Fugir"],
  ["abaixar", "Abaixar (Caído)"],
  ["parar", "Parar"],
];

const estado = {
  id: null,
  dados: null,
  mapa: "cripta_inicial",
  classe: "bardo",
  especie: "anao",
  modo: "mover",
  abaLog: "combate",
  erro: null,
  magia: null, // { nome, comando } enquanto se escolhe o alvo ou o comando
};

const painelCombate = document.getElementById("painel");
const botaoPainel = document.getElementById("painel-toggle");
const botaoTelaCheia = document.getElementById("tela-cheia");
const seletorMapa = document.getElementById("seletor-mapa");
const seletorClasse = document.getElementById("seletor-classe");
const seletorEspecie = document.getElementById("seletor-especie");
const canvasRetrato = document.getElementById("retrato");
const ctxRetrato = canvasRetrato ? canvasRetrato.getContext("2d") : null;
if (ctxRetrato) ctxRetrato.imageSmoothingEnabled = false;
const elementoD20 = document.getElementById("d20-die");
const bandejaD20 = document.getElementById("d20-tray");
const tituloD20 = document.getElementById("d20-titulo");
const resultadoD20 = document.getElementById("d20-resultado");

/**
 * Dados & Dragões — animação visual do D20.
 * O resultado real vem exclusivamente do Rule Engine.
 */
function playD20Animation(element) {
  if (!element) return;

  element.classList.remove("is-rolling");

  // Reinicia a animação CSS.
  void element.offsetWidth;

  element.classList.add("is-rolling");

  element.addEventListener(
    "animationend",
    () => {
      element.classList.remove("is-rolling");
    },
    { once: true },
  );
}

// Opcional: vincula o botão à animação visual.
function bindD20Animation(button, die) {
  if (!button || !die) return;

  button.addEventListener("click", () => {
    playD20Animation(die);
  });
}

bindD20Animation(bandejaD20, elementoD20);

function exibirRolagemD20(titulo, texto, estilo = "") {
  playD20Animation(elementoD20);
  if (tituloD20) tituloD20.textContent = titulo;
  if (resultadoD20) {
    resultadoD20.textContent = texto;
    resultadoD20.className = `d20-resultado${estilo ? " " + estilo : ""}`;
  }
}

function atualizarD20PorResultado(acao, resultado, estadoAtual) {
  if (!resultado) return;
  if (acao === "atacar" && resultado.ataque) {
    const atk = resultado.ataque;
    const d20Val = atk.rolagem_bruta ?? atk.dado ?? atk.rolagem ?? "?";
    const total = atk.total ?? d20Val;
    const acertou = Boolean(atk.acertou);
    const crit = Boolean(atk.critico);
    const dano = resultado.dano?.total;
    const sufixo = acertou && dano !== undefined ? ` (${dano} dano)` : acertou ? " ✓" : " ✗";
    exibirRolagemD20(
      crit ? "Crítico!" : "Ataque",
      `d20:${d20Val} → ${total}${sufixo}`,
      crit ? "critico" : acertou ? "" : "falha",
    );
    return;
  }
  if (acao === "conjurar") {
    const nomeMagia = resultado.magia || "Magia";
    if (resultado.ataque) {
      const atk = resultado.ataque;
      const d20Val = atk.rolagem_bruta ?? atk.dado ?? "?";
      const total = atk.total ?? d20Val;
      const acertou = Boolean(atk.acertou);
      exibirRolagemD20(nomeMagia, `d20:${d20Val} → ${total}`, acertou ? "" : "falha");
      return;
    }
    if (resultado.salvaguarda) {
      const sv = resultado.salvaguarda;
      const total = sv.total ?? "?";
      const passou = Boolean(sv.sucesso);
      exibirRolagemD20(nomeMagia, `Salv:${total} vs CD ${sv.cd ?? ""}`, passou ? "falha" : "critico");
      return;
    }
    if (resultado.curado !== undefined) {
      exibirRolagemD20(nomeMagia, `+${resultado.curado} PV`, "critico");
      return;
    }
    if (resultado.pv_temporarios_ganhos !== undefined) {
      exibirRolagemD20(nomeMagia, `+${resultado.pv_temporarios_ganhos} PV temp`, "critico");
      return;
    }
    if (resultado.dano) {
      exibirRolagemD20(nomeMagia, `${resultado.dano.total} dano`, "");
      return;
    }
    exibirRolagemD20(nomeMagia, "Ativada", "");
    return;
  }
  if (acao === "recuperar_folego" && resultado.curado !== undefined) {
    exibirRolagemD20("Recuperar Fôlego", `+${resultado.curado} PV`, "critico");
    return;
  }
  if (acao === "descansar" && resultado.curado !== undefined) {
    exibirRolagemD20("Descanso Curto", `+${resultado.curado} PV`, "critico");
    return;
  }
  if (acao === "encerrar" && estadoAtual) {
    exibirRolagemD20(`Turno ${estadoAtual.rodada}`, "Seu turno", "");
  }
}

function definirPainelAberto(aberto) {
  painelCombate.hidden = !aberto;
  botaoPainel.setAttribute("aria-expanded", String(aberto));
  botaoPainel.title = aberto ? "Fechar magias e opções" : "Abrir magias e opções";
}

function atualizarControleTelaCheia() {
  const ativo = Boolean(document.fullscreenElement);
  const rotulo = ativo ? "Sair da tela cheia" : "Ativar tela cheia";
  botaoTelaCheia.setAttribute("aria-pressed", String(ativo));
  botaoTelaCheia.setAttribute("aria-label", rotulo);
  botaoTelaCheia.title = rotulo;
  const spanRotulo = botaoTelaCheia.querySelector(".rotulo");
  if (spanRotulo) spanRotulo.textContent = ativo ? "Sair da tela cheia" : "Tela cheia";
}

const canvas = document.getElementById("mapa");
const ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = false;
const TAMANHO_QUADRO_BARDO = 32;
// A folha 4×4 segue as linhas baixo, esquerda, cima e direita; as colunas são quadros de caminhada.
const LINHA_DIRECAO_BARDO = { baixo: 0, esquerda: 1, cima: 2, direita: 3 };
const spriteBardo = new Image();
const spriteMonge = new Image();
const spriteGuerreiro = new Image();
const spriteBarbaro = new Image();
const spriteLadino = new Image();
const spriteClerigo = new Image();
const spriteMago = new Image();
const spritePaladino = new Image();
const spriteDruida = new Image();
const spriteArtifice = new Image();
const spriteGuardiao = new Image();
const spriteFeiticeiro = new Image();
const spriteBruxo = new Image();
let direcaoBardo = "direita";
let quadroBardo = 0;

function aoCarregarSprite() {
  if (estado.dados) {
    desenhar();
    desenharRetrato();
    renderizarIniciativa();
  }
}

[
  spriteBardo,
  spriteMonge,
  spriteGuerreiro,
  spriteBarbaro,
  spriteLadino,
  spriteClerigo,
  spriteMago,
  spritePaladino,
  spriteDruida,
  spriteArtifice,
  spriteGuardiao,
  spriteFeiticeiro,
  spriteBruxo,
].forEach((img) => img.addEventListener("load", aoCarregarSprite));

spriteBardo.src = "/static/assets/bardo.png";
spriteMonge.src = "/static/assets/monge.png?v=2";
spriteGuerreiro.src = "/static/assets/guerreiro.png?v=2";
spriteBarbaro.src = "/static/assets/barbaro.png?v=2";
spriteLadino.src = "/static/assets/ladino.png?v=2";
spriteClerigo.src = "/static/assets/clerigo.png?v=2";
spriteMago.src = "/static/assets/mago.png?v=2";
spritePaladino.src = "/static/assets/paladino.png?v=2";
spriteDruida.src = "/static/assets/druida.png?v=2";
spriteArtifice.src = "/static/assets/artifice.png?v=2";
spriteGuardiao.src = "/static/assets/guardiao.png?v=1";
spriteFeiticeiro.src = "/static/assets/feiticeiro.png?v=1";
spriteBruxo.src = "/static/assets/bruxo.png?v=1";

const SPRITES_CLASSE = {
  bardo: spriteBardo,
  monge: spriteMonge,
  guerreiro: spriteGuerreiro,
  barbaro: spriteBarbaro,
  ladino: spriteLadino,
  clerigo: spriteClerigo,
  mago: spriteMago,
  paladino: spritePaladino,
  druida: spriteDruida,
  artifice: spriteArtifice,
  guardiao: spriteGuardiao,
  feiticeiro: spriteFeiticeiro,
  bruxo: spriteBruxo,
};

function desenharTerreno(x, y, tipo) {
  const estiloBase = ESTILO_TERRENO[tipo] || ESTILO_TERRENO.chao;
  const tema = temaMapaAtual();
  const e = tipo === "chao"
    ? { ...estiloBase, base: tema.piso, sombra: tema.sombra }
    : estiloBase;
  const pixelTerreno = TAMANHO / 8;
  const gx = Math.round(x / TAMANHO);
  const gy = Math.round(y / TAMANHO);
  // Variação determinística: cada ladrilho mantém sua aparência entre quadros.
  const variacao = (gx * 17 + gy * 31 + gx * gy * 7) % 5;
  ctx.fillStyle = e.base;
  ctx.fillRect(x, y, TAMANHO, TAMANHO);

  // Luz suave no topo e sombra na base dão volume sem abandonar a pixel art.
  const luz = ctx.createLinearGradient(x, y, x + TAMANHO, y + TAMANHO);
  luz.addColorStop(0, tipo === "agua" ? "rgba(111, 181, 225, 0.13)" : "rgba(255, 239, 205, 0.075)");
  luz.addColorStop(1, "rgba(0, 0, 0, 0.24)");
  ctx.fillStyle = luz;
  ctx.fillRect(x, y, TAMANHO, TAMANHO);

  // Manchas e juntas de pedra com distribuição estável por casa.
  ctx.fillStyle = e.sombra;
  for (let i = 0; i < 4 + variacao; i++) {
    const px = ((gx * 7 + gy * 13 + i * 5 + variacao) % 8) * pixelTerreno;
    const py = ((gx * 3 + gy * 11 + i * 3 + variacao * 2) % 8) * pixelTerreno;
    ctx.fillRect(x + px, y + py, pixelTerreno, pixelTerreno);
  }

  if (tipo === "chao" && (gx * 13 + gy * 19) % 7 === 0) {
    // Pequenas fissuras ocasionais: detalhe de ambiente, sem poluir cada ladrilho.
    ctx.strokeStyle = "rgba(8, 7, 11, 0.48)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x + 8 + (variacao * 2), y + 7);
    ctx.lineTo(x + 13 + (variacao * 2), y + 13);
    ctx.lineTo(x + 11 + (variacao * 2), y + 19);
    ctx.stroke();
  }

  // Borda interna iluminada e base escurecida para separar visualmente as casas.
  ctx.strokeStyle = "rgba(0, 0, 0, 0.34)";
  ctx.lineWidth = 1;
  ctx.strokeRect(x + 0.5, y + 0.5, TAMANHO - 1, TAMANHO - 1);
  ctx.fillStyle = "rgba(255, 235, 190, 0.045)";
  ctx.fillRect(x + 1, y + 1, TAMANHO - 2, 1);

  if (tipo === "parede") {
    ctx.fillStyle = e.vinho;
    ctx.fillRect(x, y + TAMANHO / 2 - 1, TAMANHO, 2);
    ctx.fillRect(x + TAMANHO / 3, y, 2, TAMANHO / 2);
    ctx.fillRect(x + (TAMANHO * 2) / 3, y + TAMANHO / 2, 2, TAMANHO / 2);
    ctx.fillStyle = "rgba(0, 0, 0, 0.24)";
    ctx.fillRect(x + 2, y + 3, TAMANHO - 4, 2);
  }
  if (tipo === "porta") {
    ctx.fillStyle = "#2a1c0e";
    for (let i = 1; i < 4; i++) ctx.fillRect(x + i * (TAMANHO / 4) - 1, y, 2, TAMANHO);
    ctx.fillStyle = "rgba(255, 205, 115, 0.42)";
    ctx.fillRect(x + 3, y + 2, TAMANHO - 6, 2);
    ctx.fillStyle = "#b58a4d";
    ctx.fillRect(x + TAMANHO / 2 - 2, y + TAMANHO / 2, 4, 4);
  }
  if (tipo === "agua") {
    ctx.fillStyle = "rgba(105, 184, 229, 0.65)";
    ctx.fillRect(x + 4 + (variacao % 3), y + 9, 11, 2);
    ctx.fillRect(x + 17, y + 21 - (variacao % 2), 10, 2);
    ctx.fillStyle = "rgba(9, 28, 49, 0.42)";
    ctx.fillRect(x + 2, y + 15, TAMANHO - 4, 1);
  }
  if (tipo === "pilar") {
    ctx.fillStyle = "rgba(0, 0, 0, 0.42)";
    ctx.fillRect(x + 4, y + 7, TAMANHO - 7, TAMANHO - 7);
    ctx.fillStyle = "#241f29";
    ctx.fillRect(x + 5, y + 4, TAMANHO - 10, TAMANHO - 10);
    ctx.fillStyle = "#7a6855";
    ctx.fillRect(x + 7, y + 6, TAMANHO - 14, 4);
    ctx.fillStyle = "rgba(255, 228, 177, 0.2)";
    ctx.fillRect(x + 7, y + 6, 2, TAMANHO - 12);
  }
  if (tipo === "tocha") {
    const grad = ctx.createRadialGradient(
      x + TAMANHO / 2, y + TAMANHO / 2, 2,
      x + TAMANHO / 2, y + TAMANHO / 2, TAMANHO * 1.15,
    );
    grad.addColorStop(0, "rgba(255, 175, 65, 0.34)");
    grad.addColorStop(1, "rgba(255, 140, 30, 0)");
    ctx.fillStyle = grad;
    ctx.fillRect(x - TAMANHO, y - TAMANHO, TAMANHO * 3, TAMANHO * 3);
    ctx.fillStyle = "#6e4726";
    ctx.fillRect(x + 13, y + 14, 6, 8);
    ctx.fillStyle = "#ff9d2e";
    ctx.fillRect(x + 12, y + 8, 8, 7);
    ctx.fillStyle = "#fff1a8";
    ctx.fillRect(x + 14, y + 10, 4, 4);
  }
}

function desenharRunaCentral(largura, altura) {
  const cx = (largura * TAMANHO) / 2;
  const cy = (altura * TAMANHO) / 2;
  const raio = Math.min(largura, altura) * TAMANHO * 0.22;
  ctx.save();
  ctx.strokeStyle = temaMapaAtual().acento;
  ctx.globalAlpha = 0.3;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(cx, cy, raio, 0, Math.PI * 2);
  ctx.stroke();
  ctx.beginPath();
  ctx.arc(cx, cy, raio * 0.68, 0, Math.PI * 2);
  ctx.stroke();
  for (let i = 0; i < 8; i++) {
    const ang = (i * Math.PI) / 4;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(ang) * (raio * 0.2), cy + Math.sin(ang) * (raio * 0.2));
    ctx.lineTo(cx + Math.cos(ang) * (raio * 1.08), cy + Math.sin(ang) * (raio * 1.08));
    ctx.stroke();
  }
  ctx.restore();
}

function desenharAnelUnidade(x, y, cor, ativo = false) {
  ctx.save();
  ctx.beginPath();
  ctx.ellipse(x + TAMANHO / 2, y + TAMANHO - 4, TAMANHO * 0.42, 5, 0, 0, Math.PI * 2);
  ctx.fillStyle = ativo ? "rgba(255, 220, 145, 0.22)" : "rgba(0, 0, 0, 0.35)";
  ctx.fill();
  ctx.lineWidth = ativo ? 2.2 : 1.6;
  ctx.strokeStyle = cor;
  ctx.stroke();
  ctx.restore();
}

function desenharSombraUnidade(x, y, heroi = false) {
  // Sombra elíptica separa o sprite do piso sem borrar os pixels do personagem.
  ctx.save();
  const cx = x + TAMANHO / 2;
  const cy = y + TAMANHO - 3;
  const grad = ctx.createRadialGradient(cx, cy, 1, cx, cy, TAMANHO * 0.62);
  grad.addColorStop(0, heroi ? "rgba(0, 0, 0, 0.62)" : "rgba(0, 0, 0, 0.58)");
  grad.addColorStop(1, "rgba(0, 0, 0, 0)");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.ellipse(cx, cy, TAMANHO * 0.58, TAMANHO * 0.22, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function desenharVinhetaMapa(largura, altura) {
  // Escurece suavemente as bordas para conduzir o olhar ao centro da arena.
  const w = largura * TAMANHO;
  const h = altura * TAMANHO;
  const grad = ctx.createRadialGradient(w * 0.5, h * 0.46, Math.min(w, h) * 0.12, w * 0.5, h * 0.46, Math.max(w, h) * 0.72);
  grad.addColorStop(0, "rgba(5, 4, 8, 0)");
  grad.addColorStop(0.68, "rgba(5, 4, 8, 0.06)");
  grad.addColorStop(1, "rgba(5, 4, 8, 0.42)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);
}



function desenharSpriteEmContexto(contexto, nome, x, y, tamanho = TAMANHO) {
  const sprite = SPRITES[nome];
  if (!sprite) return;
  const grade = sprite.linhas.length || 16;
  const pixel = tamanho / grade;
  sprite.linhas.forEach((linha, linhaIdx) => {
    [...linha].forEach((c, colIdx) => {
      const cor = sprite.pal[c];
      if (!cor) return;
      contexto.fillStyle = cor;
      contexto.fillRect(x + colIdx * pixel, y + linhaIdx * pixel, Math.ceil(pixel), Math.ceil(pixel));
    });
  });
}

// Sprites maiores que a casa para manter silhuetas legíveis quando o mapa
// é reduzido para caber na tela do celular. A base continua ancorada na casa.
// Escalas ajustadas para equilibrar o tamanho do herói e dos inimigos no mapa.
const ESCALA_SPRITE_HEROI = 1.5;
const ESCALA_SPRITE_INIMIGO = 1.8;

function desenharSprite(nome, x, y) {
  const tamanho = TAMANHO * ESCALA_SPRITE_INIMIGO;
  const deslocamentoX = (TAMANHO - tamanho) / 2;
  const deslocamentoY = TAMANHO - tamanho;
  desenharSpriteEmContexto(ctx, nome, x + deslocamentoX, y + deslocamentoY, tamanho);
}

function desenharBardo(x, y) {
  const classe = (estado.dados?.personagem?.classe || "bardo").toLowerCase();
  const folha = SPRITES_CLASSE[classe] || spriteBardo;
  if (!folha.complete || folha.naturalWidth !== 128 || folha.naturalHeight !== 128) {
    desenharSprite("heroi", x, y);
    return;
  }
  const tamanho = TAMANHO * ESCALA_SPRITE_HEROI;
  ctx.drawImage(
    folha,
    quadroBardo * TAMANHO_QUADRO_BARDO,
    LINHA_DIRECAO_BARDO[direcaoBardo] * TAMANHO_QUADRO_BARDO,
    TAMANHO_QUADRO_BARDO,
    TAMANHO_QUADRO_BARDO,
    x + (TAMANHO - tamanho) / 2,
    y + TAMANHO - tamanho,
    tamanho,
    tamanho,
  );
}

function desenharRetrato() {
  if (!ctxRetrato || !estado.dados) return;
  const classe = (estado.dados.personagem?.classe || "bardo").toLowerCase();
  const folha = SPRITES_CLASSE[classe] || spriteBardo;
  ctxRetrato.clearRect(0, 0, 48, 48);
  if (folha.complete && folha.naturalWidth === 128 && folha.naturalHeight === 128) {
    ctxRetrato.drawImage(folha, 0, 0, 32, 32, 0, 0, 48, 48);
  }
}

function orientarBardo(origem, destino, avancarQuadro = false) {
  const dx = destino[0] - origem[0];
  const dy = destino[1] - origem[1];
  if (Math.abs(dx) > Math.abs(dy)) direcaoBardo = dx < 0 ? "esquerda" : "direita";
  else if (dy !== 0) direcaoBardo = dy < 0 ? "cima" : "baixo";
  if (avancarQuadro) quadroBardo = (quadroBardo + 1) % 4;
}

function barraVida(x, y, atual, maximo, aliado = false) {
  const largura = TAMANHO - 6;
  ctx.fillStyle = "#1c1212";
  ctx.fillRect(x + 3, y - 5, largura, 4);
  ctx.fillStyle = aliado ? "#4bb86d" : "#dc4545";
  ctx.fillRect(x + 3, y - 5, Math.max(0, (largura * atual) / maximo), 4);
}

function desenhar() {
  const d = estado.dados;
  if (!d) return;
  const { largura, altura, grade, legenda } = d.mapa;
  canvas.width = largura * TAMANHO;
  canvas.height = altura * TAMANHO;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (let y = 0; y < altura; y++) {
    for (let x = 0; x < largura; x++) {
      const simbolo = grade[y][x];
      desenharTerreno(x * TAMANHO, y * TAMANHO, legenda[simbolo].tipo);
    }
  }

  desenharRunaCentral(largura, altura);

  // Destaques: alcance de movimento e alvos válidos.
  if (d.de_jogador && estado.modo === "mover") {
    ctx.fillStyle = "rgba(53, 139, 242, 0.28)";
    d.alcancaveis.forEach(([x, y]) => {
      ctx.fillRect(x * TAMANHO + 1, y * TAMANHO + 1, TAMANHO - 2, TAMANHO - 2);
    });
  }
  if (d.de_jogador && estado.modo === "alvo_magia") {
    d.alvos_magia.forEach((id) => {
      const u = d.unidades.find((item) => item.id === id);
      if (!u) return;
      ctx.strokeStyle = "#c29aff";
      ctx.lineWidth = 2;
      ctx.strokeRect(u.posicao[0] * TAMANHO + 2, u.posicao[1] * TAMANHO + 2, TAMANHO - 4, TAMANHO - 4);
    });
  }
  if (d.de_jogador && (estado.modo === "atacar" || estado.modo === "golpe_bonus")) {
    d.alvos.forEach((id) => {
      const u = d.unidades.find((item) => item.id === id);
      if (!u) return;
      ctx.strokeStyle = estado.modo === "golpe_bonus" ? "#ffdc91" : "#ff5252";
      ctx.lineWidth = 2;
      ctx.strokeRect(u.posicao[0] * TAMANHO + 2, u.posicao[1] * TAMANHO + 2, TAMANHO - 4, TAMANHO - 4);
    });
  }

  // Grade tática dourada sutil.
  const forte =
    d.de_jogador &&
    (estado.modo === "mover" ||
      estado.modo === "atacar" ||
      estado.modo === "golpe_bonus" ||
      estado.modo === "alvo_magia");
  ctx.strokeStyle = forte ? "rgba(217, 166, 83, 0.24)" : "rgba(200, 195, 181, 0.09)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= largura; x++) {
    ctx.beginPath();
    ctx.moveTo(x * TAMANHO + 0.5, 0);
    ctx.lineTo(x * TAMANHO + 0.5, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y <= altura; y++) {
    ctx.beginPath();
    ctx.moveTo(0, y * TAMANHO + 0.5);
    ctx.lineTo(canvas.width, y * TAMANHO + 0.5);
    ctx.stroke();
  }

  // Luz ambiente por cima do piso, antes de desenhar unidades e indicadores.
  desenharVinhetaMapa(largura, altura);

  // Inimigos com sombra de contato e anel de seleção.
  d.unidades.forEach((u) => {
    if (u.derrotado) return;
    const [x, y] = u.posicao;
    desenharSombraUnidade(x * TAMANHO, y * TAMANHO);
    desenharAnelUnidade(x * TAMANHO, y * TAMANHO, "#dc4545", d.turno_de === u.id);
    desenharSprite(u.perfil, x * TAMANHO, y * TAMANHO);
    barraVida(x * TAMANHO, y * TAMANHO, u.pv_atuais, u.pv_maximo, false);
  });

  // Personagem com anel azul/dourado na base.
  const p = d.personagem;
  const px = p.posicao[0] * TAMANHO;
  const py = p.posicao[1] * TAMANHO;
  desenharSombraUnidade(px, py, true);
  desenharAnelUnidade(px, py, d.de_jogador ? "#ffdc91" : "#358bf2", d.de_jogador);
  desenharBardo(px, py);
  barraVida(px, py, p.pv_atuais, p.pv_maximo, true);
}

function textoRecursoSecundario(d) {
  const magias1 = (d.magias || []).filter((m) => m.circulo === 1);
  if (d.maos_consagradas) {
    const mc = d.maos_consagradas;
    return {
      pct: (mc.pool_restante / Math.max(1, mc.pool_maximo)) * 100,
      rotulo: `Mãos ${mc.pool_restante}/${mc.pool_maximo} · Mov ${d.movimento_restante_pes}/${d.personagem.deslocamento_pes} pés`,
    };
  }
  if (d.furia) {
    return {
      pct: (d.furia.usos_restantes / Math.max(1, d.furia.usos_maximos)) * 100,
      rotulo: `Fúria ${d.furia.usos_restantes}/${d.furia.usos_maximos} · Mov ${d.movimento_restante_pes}/${d.personagem.deslocamento_pes} pés`,
    };
  }
  if (d.recuperar_folego) {
    return {
      pct: (d.recuperar_folego.usos_restantes / Math.max(1, d.recuperar_folego.usos_maximos)) * 100,
      rotulo: `Fôlego ${d.recuperar_folego.usos_restantes}/${d.recuperar_folego.usos_maximos} · Mov ${d.movimento_restante_pes}/${d.personagem.deslocamento_pes} pés`,
    };
  }
  if (d.inimigo_favorito) {
    const inf = d.inimigo_favorito;
    return {
      pct: (inf.usos_restantes / Math.max(1, inf.usos_maximos)) * 100,
      rotulo: `Marca ${inf.usos_restantes}/${inf.usos_maximos} · Mov ${d.movimento_restante_pes}/${d.personagem.deslocamento_pes} pés`,
    };
  }
  if (d.feiticaria_inata) {
    const fi = d.feiticaria_inata;
    return {
      pct: (fi.usos_restantes / Math.max(1, fi.usos_maximos)) * 100,
      rotulo: `Inata ${fi.usos_restantes}/${fi.usos_maximos} · Mov ${d.movimento_restante_pes}/${d.personagem.deslocamento_pes} pés`,
    };
  }
  if (magias1.length > 0) {
    const temEspaco = magias1.some((m) => m.motivo !== "sem espaço de 1º círculo");
    return {
      pct: temEspaco ? 100 : 25,
      rotulo: `Mov ${d.movimento_restante_pes}/${d.personagem.deslocamento_pes} pés · ${d.personagem.xp ?? 0} XP · ${d.personagem.ouro_po ?? 0} PO`,
    };
  }
  return {
    pct: (d.movimento_restante_pes / Math.max(1, d.personagem.deslocamento_pes)) * 100,
    rotulo: `Mov ${d.movimento_restante_pes}/${d.personagem.deslocamento_pes} pés · ${d.personagem.xp ?? 0} XP · ${d.personagem.ouro_po ?? 0} PO`,
  };
}

function renderizarFicha() {
  const d = estado.dados;
  const p = d.personagem;
  const pctHp = Math.max(0, (p.pv_atuais / Math.max(1, p.pv_maximo)) * 100);
  const temp = p.pv_temporarios > 0 ? ` (+${p.pv_temporarios})` : "";
  const rec = textoRecursoSecundario(d);

  const badgeNivel = document.getElementById("badgeNivel");
  const badgeCa = document.getElementById("badgeCa");
  if (badgeNivel) badgeNivel.textContent = String(p.nivel);
  if (badgeCa) badgeCa.textContent = String(p.ca);
  desenharRetrato();

  const rotuloEsp = p.especie_nome || p.especie ? `${p.especie_nome || p.especie} · ` : "";
  const rotuloSub = p.subclasse_nome ? ` · ${p.subclasse_nome}` : "";
  const badgesCond = [];
  if (Array.isArray(p.condicoes) && p.condicoes.length > 0) {
    badgesCond.push(...p.condicoes);
  }
  if (p.reducao_forca > 0) {
    badgesCond.push(`-${p.reducao_forca} FOR`);
  }
  const rotuloCond = badgesCond.length > 0 ? ` · [${badgesCond.join(", ")}]` : "";
  const dicasFicha = [];
  if (Array.isArray(p.tracos_especie) && p.tracos_especie.length > 0) {
    dicasFicha.push(`Traços de ${p.especie_nome || p.especie}: ${p.tracos_especie.join(", ")}`);
  }
  if (Array.isArray(p.maestrias_arma) && p.maestrias_arma.length > 0) {
    dicasFicha.push(`Maestrias em Arma: ${p.maestrias_arma.join(", ")}`);
  }
  const attrTitle = dicasFicha.length > 0 ? ` title="${escaparHtml(dicasFicha.join(" | "))}"` : "";
  document.getElementById("ficha").innerHTML = `
    <div class="char-name"${attrTitle}>${p.nome} <small>Nv ${p.nivel} · ${rotuloEsp}${p.classe}${rotuloSub} · CA ${p.ca}${rotuloCond}</small></div>
    <div class="bar hp">
      <span style="width:${pctHp}%"></span>
      <label>${p.pv_atuais}/${p.pv_maximo}${temp} PV</label>
    </div>
    <div class="bar mp">
      <span style="width:${Math.max(0, Math.min(100, rec.pct))}%"></span>
      <label>${rec.rotulo}</label>
    </div>`;
}

function renderizarIniciativa() {
  const d = estado.dados;
  const lista = document.getElementById("iniciativa");
  lista.replaceChildren();
  const classeHeroi = (d.personagem?.classe || "bardo").toLowerCase();
  const folha = SPRITES_CLASSE[classeHeroi] || spriteBardo;
  d.iniciativa.forEach((item) => {
    const li = document.createElement("li");
    const ator = d.turno_de === item.id;
    const unidade = d.unidades.find((u) => u.id === item.id);
    const ehAliado = item.id === d.personagem.id;
    li.className = `unit-card ${ehAliado ? "ally" : "enemy"}`;
    if (ator) {
      li.classList.add("current", "ativo");
    }
    if (unidade?.derrotado) li.classList.add("derrotado");
    li.title = `${item.nome} (Iniciativa ${item.total})`;
    if (ehAliado && folha.complete && folha.naturalWidth === 128 && folha.naturalHeight === 128) {
      li.innerHTML = `<canvas class="unit-sprite" width="26" height="26" aria-hidden="true"></canvas><span class="unit-nome">${item.nome}</span><small>${item.total}</small>`;
      const c = li.querySelector("canvas");
      const cctx = c.getContext("2d");
      cctx.imageSmoothingEnabled = false;
      cctx.drawImage(folha, 0, 0, 32, 32, 0, 0, 26, 26);
    } else if (!ehAliado && unidade?.perfil && SPRITES[unidade.perfil]) {
      li.innerHTML = `<canvas class="unit-sprite" width="26" height="26" aria-hidden="true"></canvas><span class="unit-nome">${item.nome}</span><small>${item.total}</small>`;
      const c = li.querySelector("canvas");
      const cctx = c.getContext("2d");
      cctx.imageSmoothingEnabled = false;
      desenharSpriteEmContexto(cctx, unidade.perfil, 1, 1, 24);
    } else {
      const icone = ehAliado ? ICONES_CLASSE[classeHeroi] || "⚔️" : ICONES_INIMIGO[unidade?.perfil] || "💀";
      li.innerHTML = `<span class="unit-icon">${icone}</span><span class="unit-nome">${item.nome}</span><small>${item.total}</small>`;
    }
    lista.append(li);
  });
}

function renderizarMinimapa() {
  const container = document.getElementById("minimap");
  if (!container || !estado.dados) return;
  const d = estado.dados;
  const { largura, altura } = d.mapa;
  const grade = document.createElement("div");
  grade.className = "minimap-grid";

  const pontoHeroi = document.createElement("span");
  pontoHeroi.className = "dot ally";
  pontoHeroi.style.left = `${((d.personagem.posicao[0] + 0.5) / largura) * 100}%`;
  pontoHeroi.style.top = `${((d.personagem.posicao[1] + 0.5) / altura) * 100}%`;
  grade.append(pontoHeroi);

  d.unidades.forEach((u) => {
    if (u.derrotado) return;
    const ponto = document.createElement("span");
    ponto.className = "dot enemy";
    ponto.style.left = `${((u.posicao[0] + 0.5) / largura) * 100}%`;
    ponto.style.top = `${((u.posicao[1] + 0.5) / altura) * 100}%`;
    grade.append(ponto);
  });

  container.replaceChildren(grade);
}

function renderizarBarra() {
  const d = estado.dados;
  const podeAgir = d.status === "active" && d.de_jogador;
  const podeMover = d.movimento_restante_pes > 0;
  const podeUsarAcaoPrincipal = !d.acao_principal_usada;
  const temArtesMarciais = Boolean(d.artes_marciais?.ataque_desarmado_bonus);
  const folego = d.recuperar_folego;
  const furia = d.furia;
  const ladino = d.ladino;
  const recArcana = d.recuperacao_arcana;
  const maosCons = d.maos_consagradas;
  const feitInata = d.feiticaria_inata;
  const temMagias = Array.isArray(d.magias) && d.magias.length > 0;
  const temMagiaBonusDisponivel =
    temMagias && d.magias.some((m) => m.circulo === 1 && m.acao === "bonus" && m.disponivel);

  document.querySelectorAll(".botao-acao").forEach((botao) => {
    const acao = botao.dataset.acao;
    const ativo = acao === estado.modo;
    botao.classList.toggle("active", ativo);
    botao.setAttribute("aria-pressed", ativo ? "true" : "false");
    const spanTexto = botao.querySelector(".rotulo-acao");

    if (acao === "golpe_bonus") {
      botao.hidden = !temArtesMarciais;
      botao.disabled = !podeAgir || !d.acao_bonus_disponivel;
      botao.title = d.acao_bonus_disponivel
        ? "Golpe Desarmado (ação bônus de Artes Marciais)"
        : "Ação bônus já usada neste turno";
    } else if (acao === "recuperar_folego") {
      botao.hidden = !Boolean(folego);
      botao.disabled = !podeAgir || !Boolean(folego?.disponivel);
      if (spanTexto && folego) spanTexto.textContent = `Fôlego (${folego.usos_restantes})`;
      botao.title = folego?.disponivel
        ? `Recuperar o Fôlego: cura 1d10+nível (${folego.usos_restantes}/${folego.usos_maximos} usos)`
        : folego?.usos_restantes <= 0
          ? "Usos de Recuperar o Fôlego esgotados"
          : "Ação bônus já usada neste turno";
    } else if (acao === "furia") {
      botao.hidden = !Boolean(furia);
      botao.disabled = !podeAgir || !Boolean(furia?.disponivel);
      if (spanTexto && furia) spanTexto.textContent = furia.ativa ? "Em Fúria" : `Fúria (${furia.usos_restantes})`;
      botao.title = furia?.ativa
        ? "Fúria ativa (+2 de dano corpo a corpo com Força e resistência a dano físico)"
        : furia?.disponivel
          ? `Ativar Fúria (${furia.usos_restantes}/${furia.usos_maximos} usos)`
          : furia?.usos_restantes <= 0
            ? "Usos de Fúria esgotados"
            : "Ação bônus já usada neste turno";
    } else if (acao === "mirar") {
      botao.hidden = !Boolean(ladino);
      botao.disabled = !podeAgir || !Boolean(ladino?.mirar_disponivel);
      if (spanTexto && ladino) spanTexto.textContent = ladino.mirar_ativo ? "Mirando" : "Mirar";
      botao.title = ladino?.mirar_ativo
        ? "Mirar ativo: seu próximo ataque neste turno tem vantagem (+1d6 Ataque Furtivo)"
        : ladino?.mirar_disponivel
          ? "Mirar (ação bônus sem se mover): vantagem no próximo ataque e deslocamento 0"
          : d.movimento_usado_pes > 0
            ? "Mirar exige não ter se movido neste turno"
            : "Ação bônus já usada neste turno";
    } else if (acao === "recuperacao_arcana") {
      botao.hidden = !Boolean(recArcana);
      botao.disabled = !podeAgir || !Boolean(recArcana?.disponivel);
      if (spanTexto && recArcana) spanTexto.textContent = `Rec. (${recArcana.usos_restantes})`;
      botao.title = recArcana?.disponivel
        ? "Recuperação Arcana: recupera 1 espaço de magia de 1º círculo"
        : recArcana?.usos_restantes <= 0
          ? "Recuperação Arcana já utilizada"
          : "Exige ter gasto ao menos 1 espaço de magia e ação bônus livre";
    } else if (acao === "maos_consagradas") {
      botao.hidden = !Boolean(maosCons);
      botao.disabled = !podeAgir || !Boolean(maosCons?.disponivel);
      if (spanTexto && maosCons) spanTexto.textContent = `Mãos (${maosCons.pool_restante})`;
      botao.title = maosCons?.disponivel
        ? `Mãos Consagradas (ação bônus): cura usando a reserva (${maosCons.pool_restante}/${maosCons.pool_maximo} PV)`
        : maosCons?.pool_restante <= 0
          ? "Reserva de Mãos Consagradas esgotada"
          : "Ação bônus já usada neste turno";
    } else if (acao === "feiticaria_inata") {
      botao.hidden = !Boolean(feitInata);
      botao.disabled = !podeAgir || !Boolean(feitInata?.disponivel);
      if (spanTexto && feitInata) {
        spanTexto.textContent = feitInata.ativa ? "Inata Ativa" : `Inata (${feitInata.usos_restantes})`;
      }
      botao.title = feitInata?.ativa
        ? "Feitiçaria Inata ativa (+1 CD de magia e vantagem nas jogadas de ataque mágico)"
        : feitInata?.disponivel
          ? `Ativar Feitiçaria Inata (${feitInata.usos_restantes}/${feitInata.usos_maximos} usos)`
          : feitInata?.usos_restantes <= 0
            ? "Usos de Feitiçaria Inata esgotados"
            : "Ação bônus já usada neste turno";
    } else if (acao === "itens") {
      botao.disabled = true;
      botao.title = "Em breve: itens ainda não estão ligados ao combate";
    } else if (acao === "mover") {
      botao.disabled = !podeAgir || !podeMover;
      botao.title = podeMover ? "Mover pelo tabuleiro [1]" : "Deslocamento do turno esgotado";
    } else if (acao === "atacar") {
      botao.disabled = !podeAgir || !podeUsarAcaoPrincipal;
      const arma = d.arma_principal || "Arma";
      const sopro = d.sopro_draconico?.usos_restantes > 0 ? `Ataque de Sopro (${d.sopro_draconico.usos_restantes})` : null;
      const detalheArma = [arma, d.arma_distancia, sopro].filter(Boolean).join(" ou ");
      const maestrias = Array.isArray(d.personagem?.maestrias_arma) && d.personagem.maestrias_arma.length > 0
        ? ` — Maestrias: ${d.personagem.maestrias_arma.join(", ")}`
        : "";
      botao.title = podeUsarAcaoPrincipal
        ? `Atacar com ${detalheArma}${maestrias} [2]`
        : "Ação principal já usada neste turno";
    } else if (acao === "magias") {
      const podeConjurarMagia = podeUsarAcaoPrincipal || temMagiaBonusDisponivel;
      const primeiraMagia1 = (d.magias || []).find((m) => m.circulo === 1);
      const iconeMagia = botao.querySelector("#icone-magias");
      if (iconeMagia) {
        const clsIcone = CLASSE_ICONE_MAGIA[primeiraMagia1?.nome] || "spell-cura";
        iconeMagia.className = `icone spell-icon ${clsIcone}`;
      }
      botao.disabled = !podeAgir || !podeConjurarMagia || !temMagias;
      botao.title = !temMagias
        ? "Esta classe não conjura magias"
        : podeConjurarMagia
          ? "Magias de 1º círculo [4]"
          : "Ação principal já usada neste turno";
    } else if (acao === "truques") {
      const primeiroTruque = (d.magias || []).find((m) => m.circulo === 0);
      const iconeTruque = botao.querySelector("#icone-truques");
      if (iconeTruque) {
        const clsIcone = CLASSE_ICONE_MAGIA[primeiroTruque?.nome] || "spell-musica";
        iconeTruque.className = `icone spell-icon ${clsIcone}`;
      }
      botao.disabled = !podeAgir || !podeUsarAcaoPrincipal || !temMagias || !Boolean(primeiroTruque);
      botao.title = !temMagias || !primeiroTruque
        ? "Esta classe não possui truques"
        : podeUsarAcaoPrincipal
          ? "Truques [5]"
          : "Ação principal já usada neste turno";
    } else {
      botao.disabled = !podeAgir;
      botao.title = "";
    }
  });
}

function mensagemDica() {
  const d = estado.dados;
  if (estado.erro) return { texto: estado.erro, erro: true };
  if (d.status !== "active") {
    const mapaNomes = {
      bardo: "Bardo",
      monge: "Monge",
      guerreiro: "Guerreiro",
      barbaro: "Bárbaro",
      ladino: "Ladino",
      clerigo: "Clérigo",
      mago: "Mago",
      paladino: "Paladino",
      druida: "Druida",
      artifice: "Artífice",
      guardiao: "Guardião",
      feiticeiro: "Feiticeiro",
      bruxo: "Bruxo",
    };
    const rotuloClasse = mapaNomes[d.personagem?.classe] || "Herói";
    return {
      texto: d.status === "completed" ? "Vitória! Todos os inimigos caíram." : `Derrota. O ${rotuloClasse} caiu.`,
      erro: false,
    };
  }
  if (!d.de_jogador) return { texto: "Aguardando inimigos…", erro: false };
  if (estado.modo === "mover") {
    if (d.movimento_restante_pes <= 0) {
      return {
        texto: d.acao_principal_usada
          ? d.acao_bonus_disponivel
            ? "Movimento e ação principal usados; ainda pode usar sua ação bônus."
            : "Ação principal e movimento usados; encerre o turno."
          : "Movimento esgotado; ainda pode atacar ou conjurar.",
        erro: false,
      };
    }
    return {
      texto: d.acao_principal_usada
        ? `Ação principal usada. Restam ${d.movimento_restante_pes} pés de movimento.`
        : `Toque em uma casa destacada para se mover (${d.movimento_restante_pes} pés restantes).`,
      erro: false,
    };
  }
  if (estado.modo === "alvo_magia" && estado.magia) {
    return d.alvos_magia.length
      ? { texto: `Toque no inimigo destacado para lançar ${estado.magia.nome}.`, erro: false }
      : { texto: "Nenhum inimigo ao alcance da magia.", erro: false };
  }
  if (estado.modo === "magias") {
    return { texto: "Escolha uma magia no grimório.", erro: false };
  }
  if (estado.modo === "truques") {
    return { texto: "Escolha um truque no grimório.", erro: false };
  }
  if (estado.modo === "atacar") {
    const arma = d.arma_principal || "Arma";
    const sopro = d.sopro_draconico?.usos_restantes > 0 ? `Ataque de Sopro (${d.sopro_draconico.usos_restantes})` : null;
    const rotuloArma = [arma, d.arma_distancia, sopro].filter(Boolean).join(" / ");
    return d.alvos.length
      ? { texto: `Toque no inimigo destacado para atacar (${rotuloArma}).`, erro: false }
      : { texto: "Nenhum inimigo ao alcance ou com visão livre.", erro: false };
  }
  if (estado.modo === "golpe_bonus") {
    return d.alvos.length
      ? { texto: "Toque no inimigo adjacente para desferir o Golpe Desarmado bônus.", erro: false }
      : { texto: "Nenhum inimigo a 5 pés para o Golpe Desarmado bônus.", erro: false };
  }
  return { texto: "", erro: false };
}

function renderizarOpcoes() {
  const lista = document.getElementById("opcoes");
  lista.replaceChildren();
  const d = estado.dados;
  if (!d.de_jogador || d.status !== "active") return;
  if (estado.magia && estado.magia.nome === "Comando" && estado.magia.comando === undefined) {
    COMANDOS.forEach(([valor, rotulo]) => {
      lista.append(
        opcao(rotulo, "escolher comando", true, "spell-encanto", () => {
          estado.magia = { nome: "Comando", comando: valor };
          estado.modo = "alvo_magia";
          definirPainelAberto(false);
          carregarAlvosMagia("Comando");
        }),
      );
    });
    return;
  }
  if (estado.modo !== "magias" && estado.modo !== "truques") return;
  const circulo = estado.modo === "magias" ? 1 : 0;
  d.magias
    .filter((m) => m.circulo === circulo)
    .forEach((m) => {
      const aoClicar = () => {
        if (m.alvo === "si_mesmo") {
          conjurar(m.nome);
        } else if (m.alvo === "inimigo") {
          estado.erro = null;
          estado.magia = m.nome === "Comando" ? { nome: "Comando" } : { nome: m.nome };
          if (m.nome !== "Comando") {
            estado.modo = "alvo_magia";
            definirPainelAberto(false);
            carregarAlvosMagia(m.nome);
            return;
          }
          renderizarTudo();
        }
      };
      const etiqueta = m.disponivel ? (m.acao === "bonus" ? "usar (ação bônus)" : "usar") : m.motivo;
      const clsIcone = CLASSE_ICONE_MAGIA[m.nome] || (circulo === 1 ? "spell-cura" : "spell-musica");
      lista.append(opcao(m.nome, etiqueta, m.disponivel, clsIcone, aoClicar));
    });
}

function opcao(titulo, detalhe, habilitado, classeIcone, aoClicar) {
  const li = document.createElement("li");
  const botao = document.createElement("button");
  botao.type = "button";
  botao.disabled = !habilitado;
  botao.innerHTML = `<span class="spell-icon ${classeIcone}" aria-hidden="true"></span><div class="opcao-texto"><span></span><small></small></div>`;
  botao.querySelector(".opcao-texto span").textContent = titulo;
  botao.querySelector(".opcao-texto small").textContent = detalhe;
  botao.addEventListener("click", aoClicar);
  li.append(botao);
  return li;
}

async function carregarAlvosMagia(magia) {
  renderizarTudo();
}

async function conjurar(magia, alvo, comando) {
  estado.erro = null;
  const corpo = { magia };
  if (alvo !== undefined) corpo.alvo = alvo;
  if (comando !== undefined) corpo.comando = comando;
  try {
    const resposta = await chamar(`/api/encontros/${estado.id}/conjurar`, corpo);
    if (alvo !== undefined) {
      const unidade = estado.dados.unidades.find((u) => u.id === alvo);
      if (unidade) orientarBardo(estado.dados.personagem.posicao, unidade.posicao);
    }
    definirPainelAberto(false);
    estado.modo = "mover";
    estado.magia = null;
    aplicarEstado(resposta);
    atualizarD20PorResultado("conjurar", resposta.resultado, resposta.estado);
  } catch (erro) {
    estado.erro = erro.message;
    renderizarTudo();
  }
}

function formatarLinhaLog(linha, nomeHeroi) {
  const li = document.createElement("li");
  if (linha.startsWith("Recompensa:") || linha.startsWith("Avançou")) {
    li.innerHTML = `<span class="gold">${escaparHtml(linha)}</span>`;
    return li;
  }
  if (linha.includes("conjura") || linha.includes("usa Comando") || linha.includes("usa Raio") || linha.includes("usa Chicote") || linha.includes("usa Toque")) {
    li.innerHTML = `<span class="purple">${escaparHtml(linha)}</span>`;
    return li;
  }
  if (linha.includes("ataca:")) {
    li.innerHTML = `<span class="red">${escaparHtml(linha)}</span>`;
    return li;
  }
  if (nomeHeroi && linha.startsWith(nomeHeroi)) {
    li.innerHTML = `<span class="blue">${escaparHtml(linha)}</span>`;
    return li;
  }
  li.textContent = linha;
  return li;
}

function escaparHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[c]);
}

function renderizarRegistro() {
  const lista = document.getElementById("registro");
  const d = estado.dados;
  let linhas = d.log || [];
  if (estado.abaLog === "sistema") {
    const espNome = d.personagem.especie_nome || d.personagem.especie || "Anão";
    linhas = [
      `Sala: ${d.mapa.nome} (${d.mapa.largura}×${d.mapa.altura})`,
      `Raça: ${espNome} · Classe: ${d.personagem.classe} · Arma: ${d.arma_principal}`,
      `Rodada ${d.rodada} · Status: ${d.status}`,
    ];
  } else if (estado.abaLog === "geral") {
    linhas = linhas.slice(-8);
  } else {
    linhas = linhas.slice(-8);
  }
  lista.replaceChildren(...linhas.map((linha) => formatarLinhaLog(linha, d.personagem?.nome)));
  lista.scrollTop = lista.scrollHeight;
}

function ajustarMapa() {
  if (!estado.dados) return;
  const wrap = document.querySelector(".mapa-wrap");
  const { largura, altura } = estado.dados.mapa;
  const aspecto = largura / altura;
  const area = wrap.getBoundingClientRect();
  // O mapa usa a maior escala que cabe na arena inteira, atrás do HUD.
  const margemHorizontal = 12;
  const margemVertical = 12;
  let w = Math.max(1, area.width - margemHorizontal * 2);
  let h = w / aspecto;
  if (h > area.height - margemVertical * 2) {
    h = Math.max(1, area.height - margemVertical * 2);
    w = h * aspecto;
  }
  canvas.style.width = `${Math.floor(w)}px`;
  canvas.style.height = `${Math.floor(h)}px`;
}

function renderizarTudo() {
  const d = estado.dados;
  if (!d) return;
  if (seletorMapa && d.mapa?.id) {
    const mapaNormalizado = String(d.mapa.id).replaceAll("-", "_");
    estado.mapa = mapaNormalizado;
    seletorMapa.value = mapaNormalizado;
  }
  if (seletorClasse && d.personagem?.classe) {
    estado.classe = d.personagem.classe;
    seletorClasse.value = d.personagem.classe;
  }
  if (seletorEspecie && d.personagem?.especie) {
    estado.especie = d.personagem.especie;
    seletorEspecie.value = d.personagem.especie;
  }
  const turnLabel = document.getElementById("turnLabel");
  if (turnLabel) turnLabel.textContent = `Turno ${d.rodada}`;
  document.getElementById("andar").innerHTML =
    `Andar ${d.andar} · Sala ${d.sala}<small>${d.mapa.nome}</small>`;

  desenhar();
  ajustarMapa();
  renderizarFicha();
  renderizarIniciativa();
  renderizarMinimapa();
  renderizarBarra();
  renderizarRegistro();
  renderizarOpcoes();

  const dica = document.getElementById("dica");
  const msg = mensagemDica();
  dica.textContent = msg.texto;
  dica.classList.toggle("erro", msg.erro);

  const fim = document.getElementById("fim");
  fim.hidden = d.status === "active";
  document.getElementById("fim-texto").textContent = d.status === "completed" ? "✦ Vitória ✦" : "Derrota";
  const fimRecompensa = document.getElementById("fim-recompensa");
  if (d.status === "completed" && d.recompensa) {
    fimRecompensa.hidden = false;
    fimRecompensa.textContent = `Recompensa: +${d.recompensa.xp} XP · +${d.recompensa.ouro_po} PO`;
  } else {
    fimRecompensa.hidden = true;
    fimRecompensa.textContent = "";
  }
  const fimNivel = document.getElementById("fim-nivel");
  if (fimNivel) {
    if (d.status === "completed" && d.subida_nivel) {
      const carac = (d.subida_nivel.caracteristicas || []).join(", ");
      fimNivel.hidden = false;
      fimNivel.textContent = `⬆ Subiu para o Nível ${d.subida_nivel.nivel}! (+${d.subida_nivel.pv_ganhos} PV máx${carac ? " · " + carac : ""})`;
    } else {
      fimNivel.hidden = true;
      fimNivel.textContent = "";
    }
  }
  const botaoDescansar = document.getElementById("descansar");
  if (botaoDescansar) {
    const dc = d.descanso_curto;
    botaoDescansar.hidden = !(d.status === "completed" && dc);
    if (dc) {
      botaoDescansar.disabled = !dc.disponivel;
      botaoDescansar.textContent = dc.usado_na_sala
        ? `Descanso Curto usado (${dc.dados_vida_disponiveis}/${dc.dados_vida_maximos} ${dc.dado_vida})`
        : `Descanso Curto (${dc.dados_vida_disponiveis}/${dc.dados_vida_maximos} ${dc.dado_vida})`;
    }
  }
  const botaoAvancar = document.getElementById("avancar");
  botaoAvancar.hidden = !(d.status === "completed" && d.proxima_sala);
  history.replaceState(null, "", `/encontro?id=${d.encontro_id}`);
}

async function chamar(caminho, corpo) {
  const resposta = await fetch(caminho, {
    method: corpo === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json" },
    body: corpo === undefined ? undefined : JSON.stringify(corpo),
  });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.erro || "Falha na requisição");
  return dados;
}

function aplicarEstado(dados) {
  estado.dados = dados.estado || dados;
  estado.erro = null;
  renderizarTudo();
}

async function executar(acao, corpo) {
  try {
    const resposta = await chamar(`/api/encontros/${estado.id}/${acao}`, corpo);
    if (acao === "mover" && resposta.resultado?.status === "resolvido") {
      orientarBardo(estado.dados.personagem.posicao, resposta.estado.personagem.posicao, true);
    }
    if (acao === "atacar") {
      const alvo = estado.dados.unidades.find((u) => u.id === corpo.alvo);
      if (alvo) orientarBardo(estado.dados.personagem.posicao, alvo.posicao);
      estado.modo = "mover";
      estado.magia = null;
    }
    aplicarEstado(resposta);
    atualizarD20PorResultado(acao, resposta.resultado, resposta.estado);
  } catch (erro) {
    estado.erro = erro.message;
    renderizarTudo();
  }
}

function celulaDoEvento(evento) {
  const rect = canvas.getBoundingClientRect();
  const x = Math.floor(((evento.clientX - rect.left) / rect.width) * estado.dados.mapa.largura);
  const y = Math.floor(((evento.clientY - rect.top) / rect.height) * estado.dados.mapa.altura);
  return { x, y };
}

canvas.addEventListener("click", (evento) => {
  if (!estado.dados || estado.dados.status !== "active" || !estado.dados.de_jogador) return;
  const { x, y } = celulaDoEvento(evento);
  if (estado.modo === "mover") {
    if (estado.dados.alcancaveis.some(([ax, ay]) => ax === x && ay === y)) {
      executar("mover", { x, y });
    } else {
      estado.erro = "Essa casa não está ao alcance do movimento.";
      renderizarTudo();
    }
  } else if (estado.modo === "alvo_magia" && estado.magia) {
    const alvo = estado.dados.unidades.find((u) => !u.derrotado && u.posicao[0] === x && u.posicao[1] === y);
    if (alvo && estado.dados.alvos_magia.includes(alvo.id)) {
      conjurar(estado.magia.nome, alvo.id, estado.magia.comando);
    } else {
      estado.erro = "Escolha um inimigo destacado.";
      renderizarTudo();
    }
  } else if (estado.modo === "atacar" || estado.modo === "golpe_bonus") {
    const alvo = estado.dados.unidades.find((u) => !u.derrotado && u.posicao[0] === x && u.posicao[1] === y);
    if (alvo && estado.dados.alvos.includes(alvo.id)) {
      executar("atacar", { alvo: alvo.id, acao_bonus: estado.modo === "golpe_bonus" });
    } else {
      estado.erro = "Escolha um inimigo destacado.";
      renderizarTudo();
    }
  }
});

document.querySelectorAll(".botao-acao").forEach((botao) => {
  botao.addEventListener("click", () => {
    const acao = botao.dataset.acao;
    if (acao === "itens") return;
    if (acao === "recuperar_folego") {
      definirPainelAberto(false);
      estado.erro = null;
      executar("recuperar_folego", {});
      return;
    }
    if (acao === "furia") {
      definirPainelAberto(false);
      estado.erro = null;
      executar("furia", {});
      return;
    }
    if (acao === "mirar") {
      definirPainelAberto(false);
      estado.erro = null;
      executar("mirar", {});
      return;
    }
    if (acao === "recuperacao_arcana") {
      definirPainelAberto(false);
      estado.erro = null;
      executar("recuperacao_arcana", {});
      return;
    }
    if (acao === "maos_consagradas") {
      definirPainelAberto(false);
      estado.erro = null;
      executar("maos_consagradas", {});
      return;
    }
    if (acao === "feiticaria_inata") {
      definirPainelAberto(false);
      estado.erro = null;
      executar("feiticaria_inata", {});
      return;
    }
    if (acao === "encerrar") {
      definirPainelAberto(false);
      estado.erro = null;
      executar("encerrar", {});
      return;
    }
    estado.modo = acao;
    estado.erro = null;
    estado.magia = null;
    if (acao === "magias" || acao === "truques") definirPainelAberto(true);
    else definirPainelAberto(false);
    renderizarTudo();
  });
});

document.querySelectorAll(".tab[data-aba]").forEach((aba) => {
  aba.addEventListener("click", () => {
    estado.abaLog = aba.dataset.aba;
    document.querySelectorAll(".tab[data-aba]").forEach((b) => b.classList.toggle("active", b === aba));
    renderizarRegistro();
  });
});

const toolCentralizar = document.getElementById("tool-centralizar");
if (toolCentralizar) {
  toolCentralizar.addEventListener("click", () => {
    ajustarMapa();
    desenhar();
  });
}

botaoPainel.addEventListener("click", () => definirPainelAberto(painelCombate.hidden));
document.getElementById("painel-fechar").addEventListener("click", () => definirPainelAberto(false));

document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape") {
    definirPainelAberto(false);
    estado.modo = "mover";
    estado.magia = null;
    if (estado.dados) renderizarTudo();
    return;
  }
  const atalhos = { "1": "mover", "2": "atacar", "4": "magias", "5": "truques" };
  if (atalhos[evento.key]) {
    const btn = document.querySelector(`.botao-acao[data-acao="${atalhos[evento.key]}"]`);
    if (btn && !btn.disabled && !btn.hidden) btn.click();
  }
});

botaoTelaCheia.addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
    else throw new Error("não suportado");
  } catch {
    estado.erro = "Não foi possível ativar tela cheia neste navegador.";
    if (estado.dados) renderizarTudo();
  }
});
document.addEventListener("fullscreenchange", () => {
  atualizarControleTelaCheia();
  requestAnimationFrame(ajustarMapa);
});
if (!document.documentElement.requestFullscreen) botaoTelaCheia.disabled = true;
atualizarControleTelaCheia();

document.getElementById("novo").addEventListener("click", async () => {
  history.replaceState(null, "", "/encontro");
  await iniciar(true);
});

if (seletorMapa) {
  seletorMapa.addEventListener("change", async () => {
    estado.mapa = seletorMapa.value;
    history.replaceState(null, "", "/encontro");
    await iniciar(true);
  });
}

if (seletorClasse) {
  seletorClasse.addEventListener("change", async () => {
    estado.classe = seletorClasse.value;
    history.replaceState(null, "", "/encontro");
    await iniciar(true);
  });
}

if (seletorEspecie) {
  seletorEspecie.addEventListener("change", async () => {
    estado.especie = seletorEspecie.value;
    history.replaceState(null, "", "/encontro");
    await iniciar(true);
  });
}

const botaoDescansar = document.getElementById("descansar");
if (botaoDescansar) {
  botaoDescansar.addEventListener("click", async () => {
    estado.erro = null;
    await executar("descansar", { dados_vida: 1 });
  });
}

document.getElementById("avancar").addEventListener("click", async () => {
  estado.erro = null;
  try {
    const resposta = await chamar(`/api/encontros/${estado.id}/avancar`, {});
    estado.modo = "mover";
    estado.magia = null;
    aplicarEstado(resposta);
  } catch (erro) {
    estado.erro = erro.message;
    renderizarTudo();
  }
});

async function iniciar(novo = false) {
  try {
    const params = new URLSearchParams(location.search);
    const existente = params.get("id");
    let dados;
    if (existente && !novo) {
      dados = await chamar(`/api/encontros/${existente}`);
    } else {
      dados = await chamar("/api/encontros", {
        mapa_id: estado.mapa,
        classe: estado.classe,
        especie: estado.especie,
      });
    }
    estado.id = dados.encontro_id;
    estado.modo = "mover";
    aplicarEstado(dados);
    if (dados.status === "active" && !dados.de_jogador) {
      await executar("encerrar", {});
    }
    const initHeroi = (dados.iniciativa || []).find((i) => i.id === dados.personagem?.id);
    if (initHeroi) {
      exibirRolagemD20("Iniciativa", `Total ${initHeroi.total}`, "");
    }
  } catch (erro) {
    document.getElementById("dica").textContent = "Não foi possível abrir o encontro: " + erro.message;
    document.getElementById("dica").classList.add("erro");
  }
}

window.addEventListener("resize", ajustarMapa);
window.addEventListener("orientationchange", () => setTimeout(ajustarMapa, 150));

iniciar();
