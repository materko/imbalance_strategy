# MTK EMAS 1.0 — ako funguje

> V jednej vete: keď cena (alebo rýchly priemer) prekríži kĺzavý priemer smerom hore a trh je nad EMA 200, stratégia nakúpi a drží, kým ju neodstaví posúvaný stop v ATR alebo opačné kríženie.

Podľa štúdie Mac mini (iCloud KLZAKY-STUDIA, 25. 11. 2026): ~500 000 nastavení kĺzavých priemerov na MNQ, zlate, ES,
MYM a BTC. Zistenia: pod 30m kríženie nefunguje (najlepšie 1h–4h), **len longy** s filtrom **EMA 200**, často lepší
signál je **cena × jeden dlhý priemer** než kríženie dvoch, typ priemeru rozhoduje málo a **výstup viac než vstup**.

## Signál
- `signalMode` **price**: zavretie prekríži priemer `slowLen`; **cross**: priemer `fastLen` prekríži `slowLen`.
- Typ priemeru `maType`: EMA, SMA, WMA, HMA, DEMA, TEMA, RMA, VWMA, KAMA.
- Kríženie = rozdiel zmení znamienko z jedného na opačné (keď je presne nula, nepočíta sa).
- Filter trendu (spoločný filter vstupov, v profiloch zapnutý): long len nad EMA 200 toho istého grafu.
- Smer `tradeDirection` — štúdia: len longy (shorty mali PF pod 1 takmer všade).

## Vstup, stop a cieľ
- Vstup market na zavretí signálnej sviečky (plní sa na otvorení ďalšej).
- **Stop** = `slAtr` × ATR(`atrLen`) signálnej sviečky pod vstupom.
- **Posúvaný stop** = `trailAtr` × ATR pod najvyššou cenou od vstupu (späť nikdy; `trailFromR` = od akého zisku v R).
- **Zámok** (break-even): pri zisku `beAtR` R ide stop na cenu vstupu.
- **Cieľ** `rrTarget` R (0 = bez cieľa). **Opačné kríženie** obchod zavrie (`exitOnSignal`).
- Veľkosť z rizika `riskDollar` k stopu.

## Profily (najlepšie nastavenia zo štúdie)
- MNQ 4h: cena × HMA 100, stop 1,5 ATR, trailing 4 ATR + zámok pri 1R (PF 1,71); MNQ 30m DEMA 90 × 200 (PF 1,68);
  MNQ 4h EMA 5 × 13 long aj short (PF 1,64).
- Zlato, ES, MYM, BTC: kópie `mtkemasmgc`, `mtkemases`, `mtkemasmym`, `mtkemasbtc` s vlastnými profilmi.
- Málo obchodov (18–50 za rok na trh) — testuje sa ako portfólio podľa iCloud `SMERNICA-TESTOVANIA/SMERNICA_TREND_CFD.md`.

## Slovníček
- **Kĺzavý priemer** — priemerná cena posledných N sviečok; EMA a príbuzné dávajú väčšiu váhu novším.
- **ATR** — priemerná veľkosť sviečky; stop sa tak prispôsobí volatilite.
- **R** — vzdialenosť počiatočného stopu; zisk 2 R = dvojnásobok rizika.
- **C# jadro** — `mtkemasnet` (NinjaTrader 8, MetaTrader 5), zhoda s touto predlohou bar po bare.
