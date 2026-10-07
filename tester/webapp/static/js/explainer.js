/* Vysvetlivka stratégie pre začiatočníka — okno „Ako funguje táto stratégia?".
 * Text je Markdown v tradebot/strategies/<kľúč>/docs/VYSVETLIVKA.md, prichádza z
 * /api/strategies/<kľúč>/explainer. Zobrazovač pozná len to, čo vysvetlivky používajú:
 * nadpisy #, ##, odrážky -, číslované zoznamy 1., **tučné**, `kód` a odstavce. */
"use strict";

function explainerEscape(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function explainerInline(s) {
  return explainerEscape(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

function explainerHtml(md) {
  const out = [];
  let list = null;      // "ul" | "ol" | null
  let para = [];
  const flushPara = () => {
    if (para.length) { out.push(`<p>${explainerInline(para.join(" "))}</p>`); para = []; }
  };
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of md.split("\n")) {
    const line = raw.replace(/\s+$/, "");
    let m;
    if (!line.trim()) { flushPara(); closeList(); continue; }
    if ((m = line.match(/^(#{1,3})\s+(.*)$/))) {
      flushPara(); closeList();
      const lvl = m[1].length;
      out.push(`<h${lvl}${lvl === 1 ? ' id="explainer-title"' : ""}>${explainerInline(m[2])}</h${lvl}>`);
    } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      flushPara();
      if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; }
      out.push(`<li>${explainerInline(m[1])}</li>`);
    } else if ((m = line.match(/^\s*(\d+)\.\s+(.*)$/))) {
      flushPara();
      // číslovanie pokračuje aj po vnorených odrážkach (nový <ol> začne od čísla riadku)
      if (list !== "ol") { closeList(); out.push(`<ol start="${m[1]}">`); list = "ol"; }
      out.push(`<li>${explainerInline(m[2])}</li>`);
    } else if ((m = line.match(/^>\s?(.*)$/))) {
      flushPara(); closeList();
      out.push(`<p class="xp-lead">${explainerInline(m[1])}</p>`);
    } else if (list && /^\s{2,}\S/.test(raw)) {
      out[out.length - 1] = out[out.length - 1].replace(/<\/li>$/, " " + explainerInline(line.trim()) + "</li>");
    } else {
      closeList(); para.push(line.trim());
    }
  }
  flushPara(); closeList();
  return out.join("\n");
}

function explainerClose() { $("#explainer").hidden = true; }

async function explainerOpen() {
  const key = $("#strategy").value;
  const body = $("#explainer-body");
  body.innerHTML = '<p class="muted">Načítavam…</p>';
  $("#explainer").hidden = false;
  try {
    const r = await fetch(`/api/strategies/${encodeURIComponent(key)}/explainer`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    body.innerHTML = d.markdown
      ? explainerHtml(d.markdown)
      : `<h1>${explainerEscape(d.title)}</h1><p class="muted">Táto stratégia zatiaľ vysvetlivku nemá.</p>`;
  } catch (e) {
    body.innerHTML = `<p class="muted">Vysvetlivku sa nepodarilo načítať (${explainerEscape(String(e))}).</p>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("#strategy-explain")?.addEventListener("click", explainerOpen);
  $("#explainer-close")?.addEventListener("click", explainerClose);
  $("#explainer")?.addEventListener("click", (e) => { if (e.target.id === "explainer") explainerClose(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#explainer").hidden) explainerClose(); });
});
