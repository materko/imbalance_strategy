# NAS100 (Dukascopy CFD) v offline simulátore — referencia pre MultiCharts (2026-09-06)

**Účel:** mať zoznam obchodov, s ktorým sa porovná študia v MultiCharts na tých istých
dátach. **Nie je to meranie edge** — profil je `nas100_dukas_3m` (1:1 s MNQ referenčným
profilom, RR 1, trailing), fill model simulátora je naivný a poplatky ani spread sa
nepočítajú. Break-even poplatok tu preto nie je.

## Dáta

- `NAS100_M1_10Y.csv` z Dukascopy: 1m, bid strana bez spreadu, UTC, čas otvorenia baru,
  2015-01-01 až 2026-09-05 (v roku 2016 chýba ~100 dní).
- Surový súbor má 5 994 720 riadkov, z toho 2 461 494 je vypchávka (plochý bar s cenou
  predchádzajúceho uzavretia cez víkendy a prestávky). Simulátor aj prevod pre MultiCharts
  (`tradebot.tools.dukas_to_mc`, pre CFD s `--volume-scale 100`) ju zahadzujú rovnakým
  pravidlom, takže obe strany vidia tie isté 1m bary.
- Graf 3m a detekčný TF 5m sa skladajú z 1m v pamäti; vyplnenie sa rozhoduje po 1m.

```bash
.venv/Scripts/python.exe -m tradebot.tools.scan_trades --csv C:/dukas/NAS100_M1_10Y.csv \
    --profile docs/profily_archiv/ibs/nas100_dukas_3m.json --from 2024-09-04 --to 2025-09-04 --limit 0
```

## Výsledky po rokoch

| okno | zóny (limit 200) | ordre | W | L | expirované | zrušené | winrate |
|---|---|---|---|---|---|---|---|
| 20211001–20221001 | 200 | 150 | 59 | 59 | 32 | 0 | 50 % |
| 20221001–20231001 | 200 | 151 | 59 | 65 | 22 | 5 | 48 % |
| 20231001–20241001 | 200 | 153 | 75 | 55 | 21 | 2 | 58 % |
| 20240904–20250904 | 200 | 187 | 90 | 66 | 29 | 2 | 58 % |
| 20250904–20260904 | 200 | 142 | 70 | 52 | 18 | 2 | 57 % |

Január 2025 samostatne (prvé porovnávacie okno pre MultiCharts): 14 orderov, 9 W / 4 L /
1 expirovaný. Zoznam s časmi, entry, SL, TP a qty je vo výstupe príkazu vyššie s
`--from 2025-01-01 --to 2025-01-31`.

## Čo z toho plynie

- Stratégia na NAS100 generuje ~150 orderov za rok, podobne ako na BTC. Winrate pri RR 1
  je okolo 50–58 %, čo pri RR 1 a bez poplatkov znamená ľahko kladný hrubý výsledok v
  troch z piatich rokov a nulu v prvých dvoch. Reálne číslo dá až beh s poplatkami a
  spreadom (Freqtrade cesta, alebo MultiCharts s nastavenou komisiou).
- `qty` je z `legacyPineSizing` s `tickDollarValue 0.01`: jednotky po 1 USD/bod,
  `maxLossDollar 350` → qty = floor(350 / SL vzdialenosť). MNQ kontrakt je 2 USD/bod,
  takže MultiCharts s Big Point Value 1 má dať tie isté množstvá.
- Pri porovnaní s MultiCharts sedieť majú: čas zadania orderu (3m bar), entry, SL, TP,
  qty a poradie obchodov. Vyplnenie a výsledok sa môžu líšiť tam, kde 1m bar pretne SL aj
  TP naraz (simulátor berie SL) — takých barov simulátor počíta v riadku
  „nerozhodnutelnych barov".

## MultiCharts vs. simulátor, január 2025 (2026-09-07)

Študia v MultiCharts x Python beta 15.0.27717 na tých istých dátach (QuoteManager z
`NAS100_M1_mc.csv`, 5m z CSV, lebo `BarsOfData(2)` v bete padá), rovnaký profil. Obchody
MultiCharts zrekonštruované z logu študie (zmeny pozície + `ClosedEquity`):

| vstup (UTC) | simulátor | MultiCharts | zhoda |
|---|---|---|---|
| 02.01. 16:24 | LOSS | graf začína 6. 1. | mimo rozsahu |
| 06.01. 16:27 | WIN, 21674,91 | WIN vnútri baru (market vstup) | áno po oprave opakovaného vstupu |
| 13.01. 16:36 | LOSS, 20634,69 | LOSS, 20634,686 | áno |
| 14.01. 08:39 | WIN, 20923,11 | WIN vnútri baru (market vstup, 29 lotov) | áno |
| 15.01. 15:54 | LOSS, 21198,42 | LOSS, 21198,419 | áno |
| 15.01. 17:22 | WIN, 21133,63 | WIN, 21133,631 | áno |
| 17.01. 15:37 | WIN, 21395,63 | WIN, 21395,631 | áno |
| 17.01. 17:03 | WIN, 21430,90 | WIN, 21429,887 (market) | áno |
| 20.01. 15:54 | WIN, 21530,20 | WIN, 21530,197 | áno |
| 22.01. 09:06 | WIN, 21736,69 | WIN, 21736,419 (market) | áno |
| 23.01. 17:51 | expiroval | bez obchodu | áno |
| 24.01. 08:48 | LOSS, 21856,20 | LOSS, 21856,332 (market) | áno |
| 24.01. 10:54 | WIN, 21863,60 | WIN, 21863,597 | áno |
| 27.01. 20:05 | WIN, 21018,56 | WIN, 21018,564 | áno |

Všetkých 13 obchodov v rozsahu grafu má rovnaký smer a výsledok; limitky sedia na cent,
market vstupy (Pin Bar) sa líšia o cenu otvorenia ďalšieho baru, čo je správne — simulátor
ich plní naivne ako limitku. Čo bolo treba na strane adaptéra vyriešiť, je v `docs/RUNNING.md`
§E (FPU výnimky, Data2 z CSV, obchod vnútri baru, ordre s menom pri `Send`).

## Súvisiace

- Prevod dát a import do QuoteManagera: [RUNNING.md §E](RUNNING.md).
- Profil: [profily_archiv/ibs/nas100_dukas_3m.json](profily_archiv/ibs/nas100_dukas_3m.json).
- Oprava razenia času baru v MultiCharts adaptéri (čas zatvorenia → otvorenia):
  `tradebot/adapters/multicharts/signal.py`, `TradebotSignal._open_ms`.
