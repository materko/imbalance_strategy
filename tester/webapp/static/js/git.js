/* TradeBot Backtester — Git: stav, pull a push histórie. */
"use strict";

// --------------------------------------------------------------------------- //
// Git
// --------------------------------------------------------------------------- //

async function gitStatus() {
  try {
    const s = await api("/api/git/status");
    // história ide vždy do `main` — keď klon stojí inde, nech je to vidno v hlavičke
    if (s.target && s.branch && s.target !== s.branch) {
      $("#branch").textContent = `${s.branch} → ${s.target}`;
      $("#branch").title = `klon je na vetve ${s.branch}, história behov ide do ${s.target}`;
    } else if (s.target) {
      $("#branch").textContent = s.target; $("#branch").title = "";
    }
    const parts = [];
    if (s.uncommitted) parts.push(`${s.uncommitted} necommitnutých`);
    if (s.ahead) parts.push(`↑${s.ahead}`);
    if (s.behind) parts.push(`↓${s.behind}`);
    $("#git-status").textContent = parts.length ? parts.join(" · ") : "synchronizované";
  } catch (e) { $("#git-status").textContent = "git: " + e.message; }
}

async function gitAction(kind) {
  const box = $("#git-box"), out = $("#git-output"), close = $("#git-close");
  box.hidden = false; close.disabled = true; out.textContent = `git ${kind} …`;
  $("#git-title").textContent = `git ${kind}`;
  try {
    const r = await api(`/api/git/${kind}`, { method: "POST", body: kind === "push" ? JSON.stringify({ author: currentUser() }) : undefined });
    out.textContent = (r.ok ? "OK\n" : "CHYBA\n") + r.output;
    $("#git-title").textContent = `git ${kind} — ${r.ok ? "hotovo" : "chyba"}`;
    $("#git-status").textContent = r.uncommitted ? `${r.uncommitted} necommitnutých` : "synchronizované";
    if (kind === "pull" && !$("#view-history").hidden) loadRuns();
  } catch (e) { out.textContent = e.message; $("#git-title").textContent = `git ${kind} — chyba`; }
  // zavrieť sa dá až po dobehnutí — inak by výstup zmizol uprostred behu
  close.disabled = false;
}
