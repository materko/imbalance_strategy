"""Plugin agenta `telegram` (docs/LIVE.md, „Telegram“): správy z obchodného stroja zo spoolu, príkazy späť
(`/status`, `/pause`, `/flatten` …), 🧾 Obchody a 📈 Výkon z denníka obchodov.

Moduly: `service` (správy, príkazy, control súbory, `TelegramService`), `journal` (denník obchodov), `perf`
(čísla výkonu, graf equity), `reports` (prehľady pre Telegram), `plugin` (kontrakt `AgentPlugin`). Klient
Bot API a config sú zdieľané s hubom v `tradebot.live.telegram`.
"""

from .plugin import TelegramPlugin as PLUGIN

__all__ = ["PLUGIN"]
