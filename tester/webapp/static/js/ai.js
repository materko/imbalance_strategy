/* TradeBot Backtester — AI vrstva (FreqAI) na karte Nový beh. */
"use strict";

// --------------------------------------------------------------------------- //
// AI vrstva (FreqAI) na karte Novy beh
// --------------------------------------------------------------------------- //

/** Predvolby a zoznam toho, co dana strategia dovoli menit. Per strategia: kluce vie
 *  len ona sama, genericka vrstva ich menom nepozna. */
async function loadAiMeta() {
  const box = $("#ai-adjust");
  if (!box) return;
  try {
    const m = await api(`/api/ai/meta?strategy=${encodeURIComponent(state.strategy)}`);
    state.aiMeta = m;
    const d = m.defaults || {};
    if (!$("#ai-minprob").value) $("#ai-minprob").value = d.min_probability ?? 0.55;
    if (!$("#ai-train").value) $("#ai-train").value = d.train_period_days ?? 730;
    if (!$("#ai-backtest").value) $("#ai-backtest").value = d.backtest_period_days ?? 180;
    if (!$("#ai-model").value) $("#ai-model").value = d.model || "LightGBMClassifier";
    box.innerHTML = (m.adjustable || []).map(a => `<label class="field">
        ${esc(a.key)} <span class="hint">${esc(a.title)}</span>
        <input type="text" class="ai-range" data-key="${esc(a.key)}"
               placeholder="napr. 0.5:1.5${a.param ? ` (staticky ${esc(a.param)})` : ""}">
      </label>`).join("");
  } catch (e) {
    box.innerHTML = `<p class="an-note">${esc(e.message)}</p>`;
  }
}

/** Zadanie AI vrstvy do tela behu; `null` = vypnuta, teda parita s Pine ostava. */
function aiBody() {
  if (!$("#ai-enabled")?.checked) return null;
  const adjust = {};
  for (const el of $$("#ai-adjust .ai-range")) {
    const text = el.value.trim();
    if (!text) continue;
    const [a, b] = text.split(":").map(x => Number(x.trim()));
    if (!Number.isFinite(a) || !Number.isFinite(b) || a <= 0 || b <= 0) {
      throw new Error(`${el.dataset.key}: rozsah chce tvar OD:DO, napr. 0.5:1.5`);
    }
    adjust[el.dataset.key] = [a, b];
  }
  return {
    enabled: true,
    min_probability: Number($("#ai-minprob").value),
    train_period_days: Number($("#ai-train").value),
    backtest_period_days: Number($("#ai-backtest").value),
    model: $("#ai-model").value.trim() || undefined,
    ...(Object.keys(adjust).length ? { adjust } : {}),
  };
}

/** Nech je vidiet, co zapnutie znamena — parita a cas behu su realne naklady. */
function aiWarn() {
  const box = $("#ai-warn");
  if (!box) return;
  const zapnute = $("#ai-enabled")?.checked;
  box.hidden = !zapnute;
  if (!zapnute) return;
  const prah = Number($("#ai-minprob").value);
  const veta = prah > 0
    ? `Filter je zapnutý na prahu ${fmt(prah, 2)}. Model predpovedá pravdepodobnosť výhry,
       takže prah patrí <b>nad winrate stratégie</b>, nie nad 0,5 — pri winrate okolo 35 %
       zahodí prah 0,55 skoro všetko.`
    : "Filter je vypnutý (prah 0), obchody sa nezahadzujú — mení sa len plán podľa istoty.";
  box.innerHTML = `${veta} Beh bude pomalší (model sa trénuje walk-forward) a výsledok
    <b>nie je porovnateľný</b> s behmi bez AI: parita s Pine platí len pre vypnutú vrstvu.`;
}
