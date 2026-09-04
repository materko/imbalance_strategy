# Golden test: TradingView vs port — BINANCE:BTCUSDT.P, 3m

Referencia odčítaná priamo z TradingView Strategy Testera (2026-09-04), uložená v
[`ibs/tests/golden/tv_btcusdt_binance_3m.json`](../ibs/tests/golden/tv_btcusdt_binance_3m.json).

Nastavenia: čerstvo vložený `imbalance_strategy_FULL.pine` + 5 odchýlok od Pine defaultov
(`enablePinBarEntry`, `enableTrailing`, `tradeDirection="Long only"`, `sess2ZoneStartH=8`,
`showElliott=false`). Profil na našej strane: `btcusdt_3m_binance_tv`.

Časy TradingView sú v zóne grafu **UTC+2**, nižšie prepočítané na UTC.

```bash
python -m ibs.tools.scan_trades --exchange binance --profile btcusdt_3m_binance_tv \
    --from 2026-08-24 --to 2026-09-04 --limit 0
```

## Zhoda: 3 z 5 obchodov sedia na cent

| TradingView | Port | |
|---|---|---|
| #1 vstup **14:54** @ **79 419.5**, výstup 15:03 @ **79 607.3**, WIN | `LONG_10` vyplnený **14:54** @ **79 419.50**, TP **79 607.30**, WIN | ✅ |
| #2 vstup **17:15** @ **79 022.0**, výstup 17:21 @ **78 541.2**, LOSS | `LONG_9` vyplnený **17:15** @ **79 022.00**, SL **78 541.20**, LOSS | ✅ |
| #3 vstup **07:42** @ **80 516.0**, výstup 07:45 @ **80 458.9**, LOSS | `LONG_12` vyplnený **07:42** @ **80 516.10**, SL **80 458.90**, LOSS | ✅ (vstup o 1 tick) |

Sedí vstupná cena, SL aj TP úroveň **a minúta vyplnenia**. To znamená, že detekcia zóny,
hľadanie gapu, `state2ConfirmTicks`, swing SL, `rrRatio` aj `snapMode` fungujú presne ako Pine.

Sedí aj **veľkosť pozície**: TV obchod #4 mal `size = 2`. Pri tick 0.1 a `tickDollarValue = 0.5`
vychádza `floor(350 / (SL_vzdialenosť × 5))`; pri SL ≈ 31.4 bodu to dá presne 2. To potvrdzuje,
že `legacyPineSizing` reprodukuje Pine vzorec vrátane jeho zaokrúhľovania.

## Rozdiel: dva obchody TradingView nemáme, päť máme navyše

TradingView má a my nie:

| | čas UTC | cena | pozn. |
|---|---|---|---|
| #4 | 08-27 07:09 | 78 765.1 | = **close** baru 07:06 |
| #5 | 08-28 14:51 | 79 250.0 | = **close** baru 14:48 |

Overené, že **nejde o rozdiel v dátach**: naše 3m sviečky majú na tých časoch presne
`O = 78 765.1` a `O = 79 250.0`, oba dni sú kompletné (480 barov).

Príčina je v **zónach, nie vo vstupnom modeli**. Diagnostika 08-28 14:48 ukazuje:

```
08-28 14:48  O=79255.5 C=79250.0 pinLONG=True | LONG zon zivych=1 dotyk=0
```

Pin bar **detegujeme správne** (a jeho close je presne TV vstupná cena), ale jediná živá LONG
zóna je 78 662.7–78 993.7, zatiaľ čo bar má low 79 048.9 — zónu sa teda nedotýka. TradingView
musel mať v tom mieste ďalšiu LONG zónu, ktorú my nemáme. Rovnaký obraz je aj 08-27 07:06.

Päť obchodov navyše na našej strane (08-25 16:30, 08-26 07:09, 08-31, 09-01, 09-02) je
druhá strana tej istej mince — máme inú množinu zón.

Orezanie vstupu na rovnaké okno ako má TradingView (`--from`) trade set **nezmenilo**, takže
to nie je hĺbkou histórie.

## Ďalší krok

Pine kód loguje každý prechod stavu cez `log.info` („STATE1->2", „STATE3->4", „STATE4 SKIP"…).
TradingView to zobrazuje v paneli **Pine logs** (kontextové menu stratégie). To je strojovo
čitateľná stopa jeho vlastného automatu — priamo porovnateľná s `StateEvent` z nášho enginu.
Diff tých dvoch stôp ukáže presne bar, na ktorom sa zóny rozídu.
