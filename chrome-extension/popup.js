async function callApi() {
  const resp = await fetch("http://localhost:8000/next", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trigger: "extension" })
  });
  const status = resp.status;
  let data = null;
  try { data = await resp.json(); } catch (_) { data = null; }
  return { status, data };
}

// --- Nova função: coleta cabeçalhos do THEAD e linhas do TBODY ---
// --- Nova versão: traz TODO o conteúdo visível da página ---
// --- Nova versão: traz TODO o conteúdo visível da página (e iframes same-origin) ---
function collectTableFromCard() {
  try {
    const collectFromDoc = (doc) => {
      if (!doc) return "";
      // innerText pega o TEXTO renderizado (respeita display/visibility)
      return (doc.body && doc.body.innerText) ||
        (doc.documentElement && doc.documentElement.innerText) ||
        "";
    };

    // 1) Texto do documento principal
    const parts = [];
    const mainText = collectFromDoc(document);
    if (mainText.trim()) parts.push(mainText);

    // 2) Texto de iframes/frame MESMA ORIGEM (se acessíveis)
    const frames = Array.from(document.querySelectorAll("iframe, frame"));
    for (const fr of frames) {
      try {
        const fdoc = fr.contentDocument || (fr.contentWindow && fr.contentWindow.document);
        const ftxt = collectFromDoc(fdoc);
        if (ftxt && ftxt.trim()) {
          const src = fr.getAttribute("src") || "(iframe inline)";
          parts.push(`\n--- iframe: ${src} ---\n${ftxt}`);
        }
      } catch (_) {
        // Cross-origin: o Chrome não permite ler; ignoramos silenciosamente
      }
    }

    // 3) Normalização (menos ruído)
    const normalized = parts.join("\n")
      .replace(/\u00A0/g, " ")   // nbsp -> espaço
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();

    // Mantém compatibilidade com o renderer atual (headers/rows)
    return {
      headers: ["URL", "Título", "Conteúdo (visível)"],
      rows: [[location.href, document.title || "", normalized]]
    };
  } catch (e) {
    console.warn("collectTableFromCard error:", e);
    return { headers: [], rows: [] };
  }
}


async function runFlow(value) {
  const wait = (ms) => new Promise(res => setTimeout(res, ms));

  // 1) Preencher #mat-input-9
  const input = document.querySelector("#mat-input-9");
  if (input) {
    const proto = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
    if (proto && proto.set) proto.set.call(input, String(value ?? ""));
    else input.value = String(value ?? "");
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // 2) Encontrar e clicar botão "Pesquisar"
  const CANDIDATE_SELECTOR = [
    "button", "[role=button]",
    "input[type=button]", "input[type=submit]", "input[type=reset]", "input[type=image]"
  ].join(",");

  const isVisible = (el) => {
    const s = window.getComputedStyle(el);
    if (s.visibility === "hidden" || s.display === "none" || parseFloat(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1;
  };
  const matchesPesquisar = (el) => {
    const t = (el.innerText || "").trim().toLowerCase();
    const v = (el.value || "").trim().toLowerCase();
    const aria = (el.getAttribute("aria-label") || "").trim().toLowerCase();
    const title = (el.getAttribute("title") || "").trim().toLowerCase();
    return t.includes("pesquisar") || v.includes("pesquisar") || aria.includes("pesquisar") || title.includes("pesquisar");
  };

  let searchBtn = null;
  for (const el of document.querySelectorAll(CANDIDATE_SELECTOR)) {
    if (isVisible(el) && matchesPesquisar(el)) { searchBtn = el; break; }
  }
  if (searchBtn) {
    try { searchBtn.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (_) { }
    try { searchBtn.focus({ preventScroll: true }); } catch (_) { }
    searchBtn.click();
  }

  // 3) Esperar ~5s por resultados
  await wait(5000);

  // 4) Abrir mat-select e escolher opção 50
  let matSelect = document.querySelector("mat-select");
  if (!matSelect) matSelect = document.querySelector(".mat-mdc-select, .mat-select");
  if (matSelect) {
    const trigger = matSelect.querySelector(".mat-mdc-select-trigger, .mat-select-trigger") || matSelect;
    trigger.click();
    await wait(400);

    const optionTexts = Array.from(document.querySelectorAll(
      '.cdk-overlay-container .mat-mdc-select-panel .mdc-list-item__primary-text,        .cdk-overlay-container .mat-select-panel .mat-option-text,        .cdk-overlay-container .mat-option .mat-option-text,        .cdk-overlay-container .mat-option'
    ));
    let targetOpt = null;
    for (const el of optionTexts) {
      const txt = (el.innerText || el.textContent || "").trim();
      if (txt === "50" || txt.includes("50")) { targetOpt = el.closest(".mat-option") || el; break; }
    }
    if (targetOpt) targetOpt.click();
    else document.body.click();
  }

  // 5) Esperar mais 2s
  await wait(5000);

  // 6) Coletar cabeçalhos (thead) e linhas (tbody)
  return collectTableFromCard();
}

document.getElementById("run").addEventListener("click", async () => {
  const ok = document.getElementById("ok");
  const err = document.getElementById("err");
  const rowsEl = document.getElementById("rows");
  const headersEl = document.getElementById("headers");
  ok.style.display = "none";
  err.style.display = "none";
  rowsEl.textContent = "";
  headersEl.textContent = "";

  try {
    const { status, data } = await callApi();
    if (status === 200 && data) {
      const valor = data.valor ?? data.value ?? data.result ?? data.data ?? data.text ?? "";
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab?.id) throw new Error("Aba ativa não encontrada.");
      const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId: tab.id, allFrames: true },
        func: runFlow,
        args: [valor],
        world: "MAIN"
      });
      ok.style.display = "block";
      if (result) {
        if (result.headers?.length) headersEl.textContent = "Colunas: " + result.headers.join(" | ");
        if (result.rows?.length) {
          const lines = result.rows.map(r => r.join(" | "));
          rowsEl.textContent = lines.join("\n");
        } else {
          rowsEl.textContent = "(Sem linhas encontradas)";
        }
      } else {
        rowsEl.textContent = "(Sem dados)";
      }
      setTimeout(() => ok.style.display = "none", 3000);
    } else {
      throw new Error("Status " + status + " ou resposta inválida da API.");
    }
  } catch (e) {
    err.textContent = "Erro: " + (e?.message || e);
    err.style.display = "block";
  }
});
