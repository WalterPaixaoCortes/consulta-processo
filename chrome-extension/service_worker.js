
// service_worker.js (Manifest V3)
let running = false;

// === CONFIG ===
const BASE_URL = "http://localhost:8000";
const POLL_INTERVAL_SEC = 30;

// ---- Core flow from your working version (self-contained) ----
async function runFlowV3(value) {
  const wait = (ms) => new Promise(res => setTimeout(res, ms));
  const _text = (el) => (el?.innerText ?? el?.textContent ?? "").replace(/\s+/g, " ").trim();
  const _uniqRows = (rows) => {
    const map = new Map();
    for (const r of rows) map.set(JSON.stringify(r), r);
    return Array.from(map.values());
  };
  const isVisible = (el) => {
    if (!el) return false;
    const s = getComputedStyle(el);
    if (s.visibility === "hidden" || s.display === "none" || +s.opacity === 0) return false;
    const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1;
  };
  const safeClick = (el) => { try { el.scrollIntoView({ behavior: "auto", block: "center" }); } catch { } try { el.focus({ preventScroll: true }); } catch { }; el.click(); };

  const rowsSelector = "table tbody tr, .mat-mdc-table .mat-mdc-row, .mat-table .mat-row";
  const waitForRows = async (min = 1, timeout = 20000) => {
    const start = performance.now();
    let last = -1, stable = 0;
    while (performance.now() - start < timeout) {
      const cnt = document.querySelectorAll(rowsSelector).length;
      if (cnt >= min) {
        if (cnt === last) { if (++stable >= 2) return cnt; }
        else { stable = 0; last = cnt; }
      }
      await wait(150);
    }
    return 0;
  };

  const getRowSnapshot = () => {
    const rows = Array.from(document.querySelectorAll(rowsSelector));
    if (!rows.length) return "";
    const first = _text(rows[0]) || "";
    const mid = _text(rows[Math.floor(rows.length / 2)]) || "";
    const last = _text(rows[rows.length - 1]) || "";
    return [first, mid, last].join(" || ");
  };

  const waitForPageChange = async (prevSnap, timeout = 10000) => {
    const start = performance.now();
    while (performance.now() - start < timeout) {
      const snap = getRowSnapshot();
      if (snap && snap !== prevSnap) return true;
      await new Promise(r => setTimeout(r, 150));
    }
    return false;
  };

  const extractFromHtmlTable = (tbl) => {
    let headers = Array.from(tbl.querySelectorAll("thead th")).map(_text).filter(Boolean);
    const rows = Array.from(tbl.querySelectorAll("tbody tr")).map(tr =>
      Array.from(tr.querySelectorAll("th,td")).map(_text)
    );
    if (!headers.length && rows.length) headers = rows[0].map((_, i) => `Coluna ${i + 1}`);
    return { headers, rows };
  };

  const extractFromMatTable = (root) => {
    const tbl = root.querySelector(".mat-mdc-table, .mat-table");
    if (!tbl) return null;
    const headerCells = tbl.querySelectorAll(".mat-mdc-header-row .mat-mdc-header-cell, .mat-header-row .mat-header-cell");
    const rowEls = tbl.querySelectorAll(".mat-mdc-row, .mat-row");
    const headers = Array.from(headerCells).map(_text).filter(Boolean);
    const rows = Array.from(rowEls).map(r =>
      Array.from(r.querySelectorAll(".mat-mdc-cell, .mat-cell")).map(_text)
    );
    return { headers: headers.length ? headers : (rows[0]?.map((_, i) => `Coluna ${i + 1}`) ?? []), rows };
  };

  const extractFromVirtualScroll = async (root) => {
    const viewport = root.querySelector("cdk-virtual-scroll-viewport");
    if (!viewport) return null;
    const content = viewport.querySelector(".cdk-virtual-scroll-content-wrapper") || viewport;
    let lastH = -1, guard = 0;
    viewport.scrollTop = 0;
    await new Promise(r => setTimeout(r, 50));
    while (content.scrollHeight !== lastH && guard < 300) {
      lastH = content.scrollHeight;
      viewport.scrollTop = lastH;
      await new Promise(r => setTimeout(r, 80));
      guard++;
    }
    const mat = extractFromMatTable(viewport) || extractFromMatTable(root);
    if (mat && mat.rows.length) return mat;
    const rowSel = ".mat-mdc-row, .mat-row, [role=row], .row, li, tr, .item";
    const rows = Array.from(viewport.querySelectorAll(rowSel)).map(r => [_text(r)]).filter(r => r[0]);
    if (rows.length) return { headers: ["Linha"], rows };
    return null;
  };

  const collectBestTableFromDoc = async (doc) => {
    const results = [];
    for (const t of doc.querySelectorAll("table")) {
      const d = extractFromHtmlTable(t);
      if (d.rows.length) results.push({ kind: "html", rows: d.rows, headers: d.headers });
    }
    const mat = extractFromMatTable(doc);
    if (mat?.rows?.length) results.push({ kind: "mat", rows: mat.rows, headers: mat.headers });
    const vs = await extractFromVirtualScroll(doc);
    if (vs?.rows?.length) results.push({ kind: "virtual", rows: vs.rows, headers: vs.headers });
    if (!results.length) return null;
    results.sort((a, b) => (b.rows?.length || 0) - (a.rows?.length || 0));
    const best = results[0];
    best.rows = _uniqRows(best.rows);
    return best;
  };

  const collectTableFromCard = async () => {
    try {
      let best = await collectBestTableFromDoc(document);
      if (!best) {
        const frames = Array.from(document.querySelectorAll("iframe, frame"));
        for (const fr of frames) {
          try {
            const fdoc = fr.contentDocument || fr.contentWindow?.document;
            if (!fdoc) continue;
            const d = await collectBestTableFromDoc(fdoc);
            if (d?.rows?.length) { best = d; break; }
          } catch { }
        }
      }
      if (!best) return { headers: [], rows: [] };
      return best;
    } catch (e) {
      return { headers: [], rows: [], error: String(e?.message || e) };
    }
  };

  const getPaginator = () => document.querySelector("mat-paginator, .mat-mdc-paginator");
  const parseRange = (pag) => {
    const lbl = pag?.querySelector(".mat-mdc-paginator-range-label, .mat-paginator-range-label");
    if (!lbl) return null;
    const t = (lbl.innerText || lbl.textContent || "").replace(/\s+/g, " ").trim();
    const m = t.match(/(\d+)\s*[–-]\s*(\d+)\s*(?:de|of)\s*(\d+)/i);
    if (m) return { start: +m[1], end: +m[2], total: +m[3] };
    const m2 = t.match(/(\d+)\s*(?:de|of)\s*(\d+)/i);
    if (m2) return { start: +m2[1], end: +m2[1], total: +m2[2] };
    return null;
  };
  const findNextButtons = (pag) => {
    const selectors = [
      "button.mat-mdc-paginator-navigation-next",
      "button.mat-paginator-navigation-next",
      "button[aria-label*=Próxima]",
      "button[aria-label*=Proxima]",
      "button[aria-label*=Next]",
      ".mat-mdc-icon-button[aria-label*=Next]",
      ".mat-mdc-icon-button[aria-label*=Próxima]",
      ".mat-icon-button[aria-label*=Next]",
    ].join(",");
    return Array.from(pag.querySelectorAll(selectors)).filter(el => {
      const s = getComputedStyle(el);
      if (s.visibility === "hidden" || s.display === "none" || +s.opacity === 0) return false;
      const r = el.getBoundingClientRect(); return r.width > 1 && r.height > 1;
    });
  };
  const isDisabledBtn = (btn) => {
    return !!(btn.disabled || btn.getAttribute("disabled") === "true" ||
      btn.getAttribute("aria-disabled") === "true" ||
      btn.classList.contains("mat-mdc-button-disabled") ||
      btn.classList.contains("mat-button-disabled"));
  };
  const clickNext = async (pag) => {
    const candidates = findNextButtons(pag);
    if (!candidates.length) return false;
    const btn = candidates[0];
    if (isDisabledBtn(btn)) return false;

    const prevSnap = getRowSnapshot();
    btn.click();

    const changed = await waitForPageChange(prevSnap, 12000);
    if (!changed) {
      await waitForRows(1, 8000);
    }
    return true;
  };

  const tryInfiniteScroll = async () => {
    const docEl = document.scrollingElement || document.documentElement || document.body;
    let prevH = -1, guard = 0;
    while (docEl.scrollHeight !== prevH && guard < 100) {
      prevH = docEl.scrollHeight;
      docEl.scrollTo(0, docEl.scrollHeight);
      await new Promise(r => setTimeout(r, 200));
      guard++;
    }
  };

  try {
    // 1) Espera linhas iniciais
    await waitForRows(1, 30000);

    // 2) Tenta aumentar page size
    let matSelect = document.querySelector("mat-select, .mat-mdc-select, .mat-select");
    if (matSelect) {
      const trigger = matSelect.querySelector(".mat-mdc-select-trigger, .mat-select-trigger") || matSelect;
      if (trigger) {
        trigger.click();
        await new Promise(r => setTimeout(r, 300));
        const panel = document.querySelector(".cdk-overlay-container .mat-mdc-select-panel, .cdk-overlay-container .mat-select-panel");
        if (panel) {
          const options = Array.from(panel.querySelectorAll(".mat-option, .mdc-list-item"));
          const getTxt = (el) => (el?.innerText ?? el?.textContent ?? "").replace(/\s+/g, " ").trim();
          const opt100 = options.find(el => /\b100\b/.test(getTxt(el)));
          const opt50 = options.find(el => /\b50\b/.test(getTxt(el)));
          const toSel = opt100 || opt50;
          if (toSel) {
            toSel.click();
            await waitForRows(1, 12000);
          } else {
            document.body.click();
          }
        }
      }
    }

    // 3) Coleta e pagina
    let aggregate = { headers: [], rows: [] };
    let first = await collectTableFromCard();
    if (first?.headers?.length) aggregate.headers = first.headers;
    if (first?.rows?.length) aggregate.rows.push(...first.rows);

    const pag = getPaginator();
    if (pag) {
      const seen = new Set();
      let guard = 0;
      while (guard < 100) {
        guard++;
        const range = parseRange(pag);
        const before = aggregate.rows.length;
        const moved = await clickNext(pag);
        if (!moved) break;
        const pageData = await collectTableFromCard();
        if (pageData?.rows?.length) aggregate.rows.push(...pageData.rows);
        const snap = document.querySelector(".mat-mdc-table, .mat-table") ?
          document.querySelector(".mat-mdc-table, .mat-table").innerText.slice(0, 200) : "";
        if (seen.has(snap)) break;
        seen.add(snap);
        if (range && range.total && aggregate.rows.length >= range.total) break;
        if (aggregate.rows.length === before) break;
      }
    } else {
      await tryInfiniteScroll();
      const all = await collectTableFromCard();
      if (all?.rows?.length) {
        aggregate.headers = aggregate.headers.length ? aggregate.headers : all.headers || [];
        aggregate.rows = all.rows;
      }
    }

    aggregate.rows = _uniqRows(aggregate.rows);
    return aggregate;
  } catch (err) {
    return { headers: [], rows: [], error: String(err?.message || err) };
  }
}

// ---- API calls ----
async function apiNext() {
  const resp = await fetch(`${BASE_URL}/next`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ trigger: "extension" })
  });
  if (resp.status === 204) return null; // sem job
  if (resp.status !== 200) return null;
  try {
    const data = await resp.json();
    return data;
  } catch {
    return null;
  }
}

async function apiFinish(tabId, payload) {
  const resp = await fetch(`${BASE_URL}/finish/${tabId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content: payload })
  });
  return resp.ok;
}

// ---- Poll loop (alarms) ----
chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("poll-next", { periodInMinutes: POLL_INTERVAL_SEC / 60 });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.create("poll-next", { periodInMinutes: POLL_INTERVAL_SEC / 60 });
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "poll-next") return;
  if (running) return; // evita sobreposição
  running = true;
  try {
    const job = await apiNext();
    if (!job) return; // sem job, apenas espera próxima execução

    // pega a aba ativa
    const tabs = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
    const tab = tabs && tabs[0];
    if (!tab?.id) return;

    // injeta runFlowV3 e roda
    const valor = job.valor ?? job.value ?? job.result ?? job.data ?? job.text ?? "";
    const jobid = job.id ?? job.jobId ?? job.job_id ?? ""
    const inj = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: runFlowV3,
      args: [valor],
      world: "MAIN"
    });
    const result = inj?.[0]?.result;
    if (!result || result.error) return;

    const payload = { headers: result.headers || [], rows: result.rows || [] };
    await apiFinish(jobid, payload);
  } catch (e) {
    // silencia erros para não interromper ciclo; pode-se logar se quiser
    console.warn("poll-next error:", e);
  } finally {
    running = false;
  }
});
