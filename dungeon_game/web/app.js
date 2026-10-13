// Interface do encontro: desenha o estado recebido do servidor e envia pedidos.
// Nenhuma regra é calculada aqui; alcance e alvos vêm da API e são revalidados no backend.

const TAMANHO = 32; // pixels por casa; cada pixel de sprite ocupa 4px
const PIXEL = TAMANHO / 8;

const SPRITES = {
  heroi: {
    pal: { h: "#2b2440", s: "#e0b48a", b: "#4a6fa5", w: "#cfd8e3", e: "#111111" },
    linhas: ["..hhhh..", ".hhhhhh.", ".hsssssh", "..ssss..", ".bbbbbbw", ".bbbbbbw", "..b..b..", "..b..b.."],
  },
  goblin: {
    pal: { g: "#5fa04e", e: "#ff3b3b", d: "#2d5a2a", k: "#111111" },
    linhas: ["..gggg..", ".ggggggg", ".ggegegg", "..gggg..", ".gkkkkg.", "..dddd..", ".dd..dd.", ".d....d."],
  },
  esqueleto: {
    pal: { b: "#e8e4d6", k: "#111111" },
    linhas: ["..bbbb..", ".bbbbbb.", ".bkbbkb.", "..bbbb..", "..bkkb..", "..bbbb..", ".b.bb.b.", "..b..b.."],
  },
};

const ESTILO_TERRENO = {
  chao: { base: "#3a3a46", sombra: "#33333f", vinho: "#2e2e39" },
  parede: { base: "#1c1a26", sombra: "#242133", vinho: "#15131d" },
  porta: { base: "#6b4a2a", sombra: "#553a20", vinho: "#4a3219" },
  agua: { base: "#1f4f7a", sombra: "#1a4268", vinho: "#2a6490" },
  pilar: { base: "#4a4a58", sombra: "#3a3a46", vinho: "#5a5a68" },
  tocha: { base: "#3a3a46", sombra: "#33333f", vinho: "#2e2e39" },
};

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
  modo: "mover",
  erro: null,
  magia: null, // { nome, comando } enquanto se escolhe o alvo ou o comando
};

const canvas = document.getElementById("mapa");
const ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = false;

function desenharTerreno(x, y, tipo) {
  const e = ESTILO_TERRENO[tipo] || ESTILO_TERRENO.chao;
  ctx.fillStyle = e.base;
  ctx.fillRect(x, y, TAMANHO, TAMANHO);
  // Textura determinística: pixels escuros em posições fixas da casa.
  ctx.fillStyle = e.sombra;
  for (let i = 0; i < 8; i++) {
    const px = ((x * 7 + y * 13 + i * 5) % 8) * PIXEL;
    const py = ((x * 3 + y * 11 + i * 3) % 8) * PIXEL;
    ctx.fillRect(x + px, y + py, PIXEL, PIXEL);
  }
  if (tipo === "parede") {
    ctx.fillStyle = e.vinho;
    ctx.fillRect(x, y + TAMANHO / 2 - 1, TAMANHO, 2);
    ctx.fillRect(x + TAMANHO / 3, y, 2, TAMANHO / 2);
    ctx.fillRect(x + (TAMANHO * 2) / 3, y + TAMANHO / 2, 2, TAMANHO / 2);
  }
  if (tipo === "porta") {
    ctx.fillStyle = "#2a1c0e";
    for (let i = 1; i < 4; i++) ctx.fillRect(x + i * (TAMANHO / 4) - 1, y, 2, TAMANHO);
  }
  if (tipo === "agua") {
    ctx.fillStyle = "#5fa6d9";
    ctx.fillRect(x + 4, y + 10, 10, 2);
    ctx.fillRect(x + 18, y + 22, 10, 2);
  }
  if (tipo === "pilar") {
    ctx.fillStyle = "#2a2a34";
    ctx.fillRect(x + 6, y + 6, TAMANHO - 12, TAMANHO - 12);
    ctx.fillStyle = "#6a6a78";
    ctx.fillRect(x + 8, y + 8, TAMANHO - 16, 4);
  }
  if (tipo === "tocha") {
    ctx.fillStyle = "#ff9d2e";
    ctx.fillRect(x + 14, y + 10, 4, 6);
  }
}

function desenharSprite(nome, x, y) {
  const sprite = SPRITES[nome];
  if (!sprite) return;
  sprite.linhas.forEach((linha, linhaIdx) => {
    [...linha].forEach((c, colIdx) => {
      const cor = sprite.pal[c];
      if (!cor) return;
      ctx.fillStyle = cor;
      ctx.fillRect(x + colIdx * PIXEL, y + linhaIdx * PIXEL, PIXEL, PIXEL);
    });
  });
}

function barraVida(x, y, atual, maximo) {
  const largura = TAMANHO - 6;
  ctx.fillStyle = "#2a1414";
  ctx.fillRect(x + 3, y - 4, largura, 3);
  ctx.fillStyle = "#e04848";
  ctx.fillRect(x + 3, y - 4, Math.max(0, (largura * atual) / maximo), 3);
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

  // Destaques: alcance de movimento e alvos válidos.
  if (d.de_jogador && estado.modo === "mover") {
    ctx.fillStyle = "rgba(79, 140, 255, 0.35)";
    d.alcancaveis.forEach(([x, y]) => ctx.fillRect(x * TAMANHO, y * TAMANHO, TAMANHO, TAMANHO));
  }
  if (d.de_jogador && estado.modo === "alvo_magia") {
    d.alvos_magia.forEach((id) => {
      const u = d.unidades.find((item) => item.id === id);
      if (!u) return;
      ctx.strokeStyle = "#b07cff";
      ctx.lineWidth = 2;
      ctx.strokeRect(u.posicao[0] * TAMANHO + 2, u.posicao[1] * TAMANHO + 2, TAMANHO - 4, TAMANHO - 4);
    });
  }
  if (d.de_jogador && estado.modo === "atacar") {
    d.alvos.forEach((id) => {
      const u = d.unidades.find((item) => item.id === id);
      if (!u) return;
      ctx.strokeStyle = "#ff5252";
      ctx.lineWidth = 2;
      ctx.strokeRect(u.posicao[0] * TAMANHO + 2, u.posicao[1] * TAMANHO + 2, TAMANHO - 4, TAMANHO - 4);
    });
  }

  // Grade discreta; mais visível em movimento e ataque.
  const forte = d.de_jogador && (estado.modo === "mover" || estado.modo === "atacar" || estado.modo === "alvo_magia");
  ctx.strokeStyle = forte ? "rgba(255,255,255,0.22)" : "rgba(255,255,255,0.08)";
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

  // Unidades.
  d.unidades.forEach((u) => {
    if (u.derrotado) return;
    const [x, y] = u.posicao;
    desenharSprite(u.perfil, x * TAMANHO, y * TAMANHO);
    barraVida(x * TAMANHO, y * TAMANHO, u.pv_atuais, u.pv_maximo);
  });
  const p = d.personagem;
  desenharSprite("heroi", p.posicao[0] * TAMANHO, p.posicao[1] * TAMANHO);
  barraVida(p.posicao[0] * TAMANHO, p.posicao[1] * TAMANHO, p.pv_atuais, p.pv_maximo);

  // Contorno do personagem ativo.
  if (d.de_jogador) {
    ctx.strokeStyle = "#36c275";
    ctx.lineWidth = 2;
    ctx.strokeRect(p.posicao[0] * TAMANHO + 1, p.posicao[1] * TAMANHO + 1, TAMANHO - 2, TAMANHO - 2);
  }
}

function renderizarFicha() {
  const p = estado.dados.personagem;
  const pct = Math.max(0, (p.pv_atuais / p.pv_maximo) * 100);
  document.getElementById("ficha").innerHTML = `
    <h1>${p.nome} <small>Nv ${p.nivel} · ${p.classe}</small></h1>
    <div class="barra-vida"><div style="width:${pct}%"></div></div>
    <div class="linha"><span>PV ${p.pv_atuais} / ${p.pv_maximo}</span><span>CA ${p.ca}</span></div>
    <div class="linha"><span>Deslocamento</span><span>${p.deslocamento_pes} pés</span></div>`;
}

function renderizarIniciativa() {
  const d = estado.dados;
  const lista = document.getElementById("iniciativa");
  lista.replaceChildren();
  d.iniciativa.forEach((item) => {
    const li = document.createElement("li");
    const ator = d.turno_de === item.id;
    const unidade = d.unidades.find((u) => u.id === item.id);
    if (ator) li.classList.add("ativo");
    if (unidade && unidade.derrotado) li.classList.add("derrotado");
    const nome = document.createElement("span");
    nome.textContent = item.nome;
    const total = document.createElement("span");
    total.textContent = item.total;
    li.append(nome, total);
    lista.append(li);
  });
  document.getElementById("andar").innerHTML = `${d.mapa.nome}<small>Rodada ${d.rodada}</small>`;
}

function renderizarBarra() {
  // Ações só existem no turno do personagem e enquanto o combate está ativo.
  // Itens continua desabilitado até ser implementado.
  const podeAgir = estado.dados.de_jogador && estado.dados.status === "active";
  document.querySelectorAll(".botao-acao").forEach((botao) => {
    const acao = botao.dataset.acao;
    const ativo = acao === estado.modo;
    botao.setAttribute("aria-pressed", ativo ? "true" : "false");
    if (acao === "itens") {
      botao.disabled = true;
      botao.title = "Em breve: itens ainda não estão ligados ao combate";
    } else {
      botao.disabled = !podeAgir;
    }
  });
}

function mensagemDica() {
  const d = estado.dados;
  if (estado.erro) return { texto: estado.erro, erro: true };
  if (d.status !== "active") {
    return { texto: d.status === "completed" ? "Vitória! Todos os inimigos caíram." : "Derrota. O Bardo caiu.", erro: false };
  }
  if (!d.de_jogador) return { texto: "Aguardando inimigos…", erro: false };
  if (estado.modo === "mover") return { texto: "Toque em uma casa destacada para se mover.", erro: false };
  if (estado.magia && estado.magia.nome === "Comando" && estado.magia.comando === undefined) {
    return { texto: "Escolha o comando que o inimigo deve cumprir.", erro: false };
  }
  if (estado.modo === "alvo_magia" && estado.magia) {
    const nome = estado.magia.nome;
    return d.alvos_magia.length
      ? { texto: `Toque em um inimigo destacado para usar ${nome}.`, erro: false }
      : { texto: `Nenhum inimigo ao alcance de ${nome} (18 m).`, erro: false };
  }
  if (estado.modo === "magias") {
    return { texto: "Escolha uma magia.", erro: false };
  }
  if (estado.modo === "truques") {
    return { texto: "Escolha um truque.", erro: false };
  }
  if (estado.modo === "atacar") {
    return d.alvos.length
      ? { texto: "Toque no inimigo destacado para atacar.", erro: false }
      : { texto: "Nenhum inimigo ao alcance. Aproxime-se primeiro.", erro: false };
  }
  return { texto: "", erro: false };
}

function renderizarOpcoes() {
  // Lista de magias ou truques do modo atual; cada item traz o motivo quando indisponível.
  // Quando a magia é Comando, a lista mostra os comandos antes do alvo.
  const lista = document.getElementById("opcoes");
  lista.replaceChildren();
  const d = estado.dados;
  if (!d.de_jogador || d.status !== "active") return;
  if (estado.magia && estado.magia.nome === "Comando" && estado.magia.comando === undefined) {
    COMANDOS.forEach(([valor, rotulo]) => {
      lista.append(opcao(rotulo, "escolher", true, () => {
        estado.magia = { nome: "Comando", comando: valor };
        estado.modo = "alvo_magia";
        renderizarTudo();
      }));
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
          if (m.nome !== "Comando") estado.modo = "alvo_magia";
          renderizarTudo();
        }
      };
      lista.append(opcao(m.nome, m.disponivel ? "usar" : m.motivo, m.disponivel, aoClicar));
    });
}

function opcao(titulo, detalhe, habilitado, aoClicar) {
  const li = document.createElement("li");
  const botao = document.createElement("button");
  botao.type = "button";
  botao.disabled = !habilitado;
  botao.innerHTML = `<span></span><small></small>`;
  botao.querySelector("span").textContent = titulo;
  botao.querySelector("small").textContent = detalhe;
  botao.addEventListener("click", aoClicar);
  li.append(botao);
  return li;
}

async function conjurar(magia, alvo, comando) {
  estado.erro = null;
  const corpo = { magia };
  if (alvo !== undefined) corpo.alvo = alvo;
  if (comando !== undefined) corpo.comando = comando;
  try {
    const resposta = await chamar(`/api/encontros/${estado.id}/conjurar`, corpo);
    estado.modo = "mover";
    estado.magia = null;
    aplicarEstado(resposta);
  } catch (erro) {
    estado.erro = erro.message;
    renderizarTudo();
  }
}

function renderizarRegistro() {
  const lista = document.getElementById("registro");
  lista.replaceChildren(
    ...estado.dados.log.slice(-6).reverse().map((linha) => {
      const li = document.createElement("li");
      li.textContent = linha;
      return li;
    }),
  );
}

function ajustarMapa() {
  // Encaixa o mapa no espaço disponível mantendo a proporção da grade.
  if (!estado.dados) return;
  const wrap = document.querySelector(".mapa-wrap");
  const { largura, altura } = estado.dados.mapa;
  const aspecto = largura / altura;
  const area = wrap.getBoundingClientRect();
  let w = area.width - 4;
  let h = w / aspecto;
  if (h > area.height - 4) {
    h = area.height - 4;
    w = h * aspecto;
  }
  canvas.style.width = `${Math.floor(w)}px`;
  canvas.style.height = `${Math.floor(h)}px`;
}

function renderizarTudo() {
  const d = estado.dados;
  desenhar();
  ajustarMapa();
  renderizarFicha();
  renderizarIniciativa();
  renderizarBarra();
  renderizarRegistro();
  renderizarOpcoes();
  const dica = document.getElementById("dica");
  const msg = mensagemDica();
  dica.textContent = msg.texto;
  dica.classList.toggle("erro", msg.erro);
  const fim = document.getElementById("fim");
  fim.hidden = d.status === "active";
  document.getElementById("fim-texto").textContent = d.status === "completed" ? "Vitória" : "Derrota";
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
    aplicarEstado(resposta);
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
  } else if (estado.modo === "atacar") {
    const alvo = estado.dados.unidades.find((u) => !u.derrotado && u.posicao[0] === x && u.posicao[1] === y);
    if (alvo && estado.dados.alvos.includes(alvo.id)) {
      executar("atacar", { alvo: alvo.id });
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
    if (acao === "encerrar") {
      estado.erro = null;
      executar("encerrar", {});
      return;
    }
    estado.modo = acao;
    estado.erro = null;
    estado.magia = null;
    renderizarTudo();
  });
});

document.getElementById("novo").addEventListener("click", async () => {
  history.replaceState(null, "", "/encontro");
  await iniciar(true);
});

async function iniciar(novo = false) {
  try {
    const params = new URLSearchParams(location.search);
    const existente = params.get("id");
    let dados;
    if (existente && !novo) {
      dados = await chamar(`/api/encontros/${existente}`);
    } else {
      dados = await chamar("/api/encontros", {});
    }
    estado.id = dados.encontro_id;
    estado.modo = "mover";
    aplicarEstado(dados);
  } catch (erro) {
    document.getElementById("dica").textContent = "Não foi possível abrir o encontro: " + erro.message;
    document.getElementById("dica").classList.add("erro");
  }
}

window.addEventListener("resize", ajustarMapa);
window.addEventListener("orientationchange", () => setTimeout(ajustarMapa, 150));

iniciar();
