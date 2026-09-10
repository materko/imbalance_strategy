# Základná analytika stratégie — v čom je dobrá a kde má chyby

Backtest odpovedá na otázku o **behu**: koľko zarobil, koľko bol drawdown. Otázka, ktorá
rozhoduje o tom, či sa so stratégiou má ďalej niečo robiť, je iná — **aká je tá
stratégia**. Na tú sa nedá odpovedať jedným behom ani jedným číslom, a hlavne sa na ňu
nedá odpovedať zakaždým inak: dve stratégie (ani tá istá o mesiac neskôr) sa nedajú
porovnať, keď sa každá merala inak.

Preto má každá stratégia v registry **jeden generovaný dokument**
`tradebot/strategies/<key>/docs/ANALYTIKA.md`, ktorý vzniká jedným príkazom:

```bash
PY -m tester.webapp.cli checkup --strategy ibs \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json --timeframe 3m
```

Príkaz spustí päť referenčných okien (behy ostanú v histórii ako každý iný), nad ich
obchodmi prejde celú batériu a dokument prepíše. Ručné úpravy v ňom nemajú zmysel —
nabudúce sa stratia; čo treba doplniť rukou, patrí do merania v `docs/merania/`.

Bez zápisu (len výpis do konzoly) `--no-write`, z hotových behov namiesto nových
`--runs <id>,<id>,…`, iné okná `--windows`.

## Čo batéria meria a prečo práve to

| krok | odpovedá na | modul |
|---|---|---|
| **päť referenčných okien** | drží znamienko po rokoch, alebo celý súčet nesie jeden rok? | `cli run` |
| **charakter** | prerazenie, trend, protitrend, scalp, formácia, swing — a teda čo je normálne | [`tester/character.py`](../tester/character.py), [TYPY_STRATEGII.md](TYPY_STRATEGII.md) |
| **skupiny obchodov** | ktorá časť obchodov výsledok kazí a či sa to dá odfiltrovať | [`tester/analytics.py`](../tester/analytics.py) |
| **test proti náhode** | je ten edge odlíšiteľný od hodu mincou — a nie je celý len v tom, *kedy* obchoduje? | [`tester/nulltest.py`](../tester/nulltest.py) |
| **slabne edge?** | drží to aj dnes, alebo sa zarobilo v prvých rokoch a odvtedy stratégia stojí? | [`tester/decay.py`](../tester/decay.py) |
| **Monte Carlo** | aký široký je interval okolo nameraného čísla a čo to robí s účtom | [`tester/montecarlo.py`](../tester/montecarlo.py) |

Nič z toho nie je nové — nové je, že to je **jedna vec s jedným výstupom**. Poradie nie je
náhodné: každý ďalší krok má zmysel len vtedy, keď predošlý nespadol. Charakter zo 40
obchodov je hádanie; skupiny obchodov stratégie, ktorá nie je lepšia než náhoda, sú
skupiny šumu; interval okolo čísla, ktoré v troch z piatich rokov bolo záporné, je
presné vyjadrenie neistoty o niečom, čo nefunguje.

Dva z tých krokov sa pýtajú na to isté z opačných strán a práve preto sú tu obidva:
**okná** hovoria, či to fungovalo rovnomerne **po rokoch**, **úpadok** hovorí, či to drží
**dnes** — päť rokov v pluse a posledný rok mimo intervalu vlastnej minulosti je stále
zisková stratégia, s ktorou sa nemá začínať.

## Ako sa číta výstup

Dokument má hore dva zoznamy: **V čom je dobrá** a **Kde má chyby**. Sú to pravidlá nad
zmeranými číslami (`checkup.verdicts()`), nie skóre a nie model — a každá veta nesie
číslo, z ktorého vznikla. Dôvod je ten istý ako pri zaraďovaní charakteru: „break-even
0,0656 % je nad poplatkom 0,05 %" je tvrdenie, s ktorým sa dá pracovať, kým „skóre 7,4"
nie je. Jedno číslo by navyše muselo tvrdiť, že drawdown, počet obchodov a odlíšiteľnosť
od náhody sa dajú spočítať na jednu hromadu.

Čo sa **nedalo zmerať, sa nehodnotí**. Chýbajúca hodnota nie je ani plus, ani mínus —
dokument nemá tvrdiť viac, než sa vie.

Hranice, na ktorých pravidlá stoja, a prečo sú tam:

| pravidlo | hranica | prečo |
|---|---|---|
| málo obchodov | pod 30 spolu | pod tým je bootstrapový interval taký široký, že závery z neho sú anekdota (tá istá hranica ako v Monte Carle) |
| edge nad poplatkom | break-even > poplatok, `P(edge > poplatok)` ≥ 95 % | poplatok je jediná istá vec v celom výpočte; nameraný break-even je bod, interval je odpoveď |
| odlíšiteľné od náhody | ≥ 2 sigma | pod tým rozdiely takej veľkosti náhoda robí bežne |
| edge je len v čase | `anytime` − `session` > 1 sigma | keď je stratégia lepšia než náhoda kedykoľvek, ale nie než náhoda v tých istých hodinách, jej edge je v tom, KEDY obchoduje — a to sa dá mať aj bez nej |
| drawdown | 95. percentil ≥ 25 % | nad tým to bežný účet neustojí, aj keď je stratégia zisková |
| slabnúci edge | posledné obdobie pod 5. percentilom vlastnej minulosti | kratší úsek je prirodzene rozkolísanejší, tak sa neporovnáva s celkom, ale s rozdelením úsekov tej istej dĺžky |
| výstupy na čase | ≥ 20 % obchodov | toľko obchodov nekončí na pláne, ale na konci seansy: je to nastavenie okna, nie vlastnosť vstupu |
| najhoršia skupina | zlepšenie ≥ 0,01 break-even | menej je šum; a keď je tá skupina väčšina obchodov, nie je to filter, ale nastavenie parametra |

## Čo v analytike nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie
  matica: `cli matrix --pairs all --timeframes 3m` (prahy sa prepočítajú na `atr`).
- **Druhý engine.** Čísla sú z jedného enginu. Signály sú v oboch rovnaké, fill model nie —
  záver pre MultiCharts patrí emulátoru (`--engine multicharts`), viď
  [STRATEGIE.md](STRATEGIE.md#oba-enginy-nie-je-odporúčanie-ale-podmienka).
- **Hľadanie lepších parametrov.** Analytika je fotka stratégie, aká je dnes. Keď sa na
  nej niečo nepáči, ďalší krok je `cli sweep`, `cli hyperopt` a
  [HYPEROPT.md](HYPEROPT.md) — nie prepisovanie fotky.
- **Pretrénovanie.** Bootstrap ho nemeria (obchody preladenej konfigurácie naozaj ziskové
  boli). Proti nemu chránia len dáta, ktoré optimalizátor nevidel.

## Kedy sa má prepočítať

Vždy, keď by dokument prestal platiť: po zmene defaultov alebo referenčného profilu
stratégie, po zmene enginu alebo fill modelu, po doplnení dát a pred akýmkoľvek záverom
typu „táto stratégia je/nie je dobrá". Je to lacné — päť rokov s 1m detailom je pár minút
a behy sa dajú znovu použiť (`--runs`).

## Čo musí stratégia dodať, aby sa dala celá zmerať

Väčšina batérie je generická: `trades.json` píše Freqtrade rovnako pre každú stratégiu
a sviečky páru sú spoločné. Štyri veci ale vie len stratégia a deklaruje ich v
`StrategySpec` ([STRATEGIE.md](STRATEGIE.md)):

| chcem v analytike | treba v `SPEC` | bez toho |
|---|---|---|
| vzdialenosť stopu a plánovaný RR obchodu | `sl_kind`, `tp_kind` (druhy kresieb, ktoré nesú SL a TP box) | tie dve vlastnosti sa jednoducho nepočítajú |
| prepočet výsledku na iný účet a odporúčanie rizika | `risk_field` (pole s dolárovým rizikom), `fixed_size_field` | Monte Carlo obchody len premieša |
| odkaz „preladiť tento parameter" | `hyperopt_cls.FEATURE_PARAMS` | analytika povie, čo kazí výsledok, ale nie čím sa to dá zmeniť |
| spárovanie obchodu s kresbou | `enter_tag` v tvare `<prefix><čas baru v ms>` a kresba s tým istým `x1_ms` | plán obchodu sa k obchodu nepriradí |

Stratégia, ktorá nedeklaruje nič, sa zmerať dá tiež — dostane menej riadkov, nie chybu.
Ale ukážková `demo_breakout` deklaruje všetko práve preto, aby bolo z čoho kopírovať.

Súvisiace: [STRATEGIE.md](STRATEGIE.md) (ako sa stratégia píše),
[TYPY_STRATEGII.md](TYPY_STRATEGII.md) (čo znamená charakter),
[HYPEROPT.md](HYPEROPT.md) (čo robiť s tým, čo analytika našla),
[../tester/AI_TESTING.md](../tester/AI_TESTING.md) (celý postup testovania).
