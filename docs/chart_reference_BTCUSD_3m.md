# Referenčné vykreslovanie — BTCUSD 3m (Coinbase), 2026-09-02/03

Popis toho, čo stratégia kreslí na graf. **Cieľ portu do Pythonu/Freqtrade: vizuálne aj logicky
rovnaké výstupy** (rovnaké zóny, rovnaké entry/SL/TP, rovnaké značky).

## Dashboard (Top Right)
```
DASHBOARD            BTCUSD
[mini sviečkový sparkline]     USD
47%  WINRATE   (8W / 9L)
OBCHODY: 17    (8W / 9L)
SERIA:   3x výhra          (zelené pozadie)
POZICIA: Žiadna
BEST WIN STREAK:  3x
WORST SL STREAK:  4x
RISK / OBCHOD:    $350
```
→ 17 obchodov, 8W/9L = 47 % winrate, RR 1:1, Long only.

## Objekty kreslené na grafe

| Objekt | Vzhľad | Poznámka |
|---|---|---|
| **Session okná** | Zvislé farebné pásy pozadia — ružový a zelenkastý | Ružový = jedno session okno, zelený = druhé (zóna vs. trade window) |
| **SD zóny** | Vodorovné obdĺžniky: **modré = Demand (long)**, **červené/ružové = Supply (short)** | Predlžujú sa doprava do expirácie / invalidácie |
| **Imbalance sviečky** | Menší tmavší box vnútri/pri zóne | `showImbalance` = zap |
| **Market structure** | Textové značky `BOS`, `CHoCH`, `HH`, `LH` + vodorovné čiary | `[len FULL]` |
| **S/R úrovne** | Vodorovné čiary cez celý graf (viac úrovní, tenké) | `[len FULL]` |
| **Liquidity sweep** | Značky `X ↑` / `X ↓` s bodkovanou čiarou | `[len FULL]` |
| **SKIP značky** | Sivé/modré štítky `SKIP`, `SKIP (SHORT)`, `…MER VYP` (smer vypnutý) | Zóna nájdená, ale obchod preskočený — pri `Long only` sú všetky SHORT zóny SKIP |
| **Counter badges** | Malé oranžové/červené bublinky pri pravom okraji zóny (`2x`, `3x`, `4x`, `5x`) | Počítadlo dotykov/pokusov zóny |
| **Entry značka** | Šípka + popis `LONG_257` a `+1` | číslo = ID obchodu |
| **TP značka** | `-1` + `TP` so šípkou nadol | výstup na TP |
| **EXPIRED značka** | Oranžový štítok `EXPIRED bar=10` | order sa nevyplnil do `state5MaxBars` = 10 barov |

## Konkrétne scény zo screenshotov (na verifikáciu portu)

1. **02 Sep '26 ~14:39–17:30** — LONG obchod `LONG_257` pri ~76 700, TP zásah krátko po vstupe,
   a hneď vedľa `EXPIRED bar=10` order, ktorý sa nevyplnil. Dobrý testcase pre timeout logiku.
2. **02 Sep '26 ~14:00–18:00** — hustá oblasť prekrývajúcich sa demand (modrých) a supply
   (červených) zón s viacerými `CHoCH`. Testcase pre `maxSdZones` + prekrývanie zón.
3. **03 Sep '26 ~09:00–12:00** — klaster `SKIP` / `SKIP (SHORT)` štítkov (smer obchodov = Long only).
4. **03 Sep '26 ~14:30–20:30** — silný uptrend so sériou `BOS`, viacero supply zón nad cenou,
   badge počítadlá `2x`/`3x`/`4x`/`5x` pri ~78 200–79 200.

## Chart nastavenia TradingView
- Symbol: `BTCUSD` / Coinbase
- Timeframe: **3m** (skript číta TF automaticky cez `timeframe.multiplier`)
- Zobrazený časový offset: UTC+2
