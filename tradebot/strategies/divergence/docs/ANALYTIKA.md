# Základná analytika — Divergence — divergencie indikátorov v smere supertrendu (`divergence`)

Zmerané 2026-09-11 na `BTC/USDT:USDT` 15m, engine `freqtrade`, poplatok 0.0500 % na stranu (Binance USDⓈ-M taker, VIP 0), profil `binance_btcusdt_15m`.

Dokument je **generovaný** — píše ho `cli checkup` celý znova, ručné úpravy sa stratia. Čo tu je a prečo práve to: [docs/ANALYTIKA.md](../../../../docs/ANALYTIKA.md).

```bash
python -m tester.webapp.cli checkup \
   --strategy divergence \
   --profile binance_btcusdt_15m \
   --timeframe 15m
```

## V čom je dobrá

- break-even 0.0737 % je nad poplatkom 0.0500 % (rezerva +0.0237 bodu)
- drawdown drží: 95. percentil 18.3 %

## Kde má chyby

- zisková v 2 z 5 referenčných okien (20211001-20221001, 20240904-20250904, 20250904-20260904 v strate)
- len 14 obchodov spolu: pod 30 je každý interval taký široký, že závery z neho sú anekdota
- edge nad poplatkom len v 55 % vzoriek — v zvyšku by burza zobrala viac, než stratégia zarobí
- proti náhode len +0.2 sigma: náznak, nie dôkaz
- charakter: formácia / štruktúra (istota slabá) — zaradenie je neisté, závery o tom, čo je pri nej normálne, treba brať opatrne

## Päť referenčných okien

Jeden rok o stratégii nepovie nič; rozhoduje **znamienko po rokoch**, nie súčet.

| okno | obchodov | PnL % | break-even % | max DD % | WR % | beh |
|---|---|---|---|---|---|---|
| 20211001-20221001 | 0 | +0.00 | - | 0.0 | 0.0 | `20260911-213554-9d11f4` |
| 20221001-20231001 | 2 | +4.52 | 0.3384 | 1.6 | 50.0 | `20260911-213614-c52533` |
| 20231001-20241001 | 1 | +0.42 | 0.1748 | 0.0 | 100.0 | `20260911-213634-9559c1` |
| 20240904-20250904 | 6 | -0.24 | 0.0397 | 6.8 | 33.3 | `20260911-213654-de5eb6` |
| 20250904-20260904 | 5 | -2.81 | -0.0626 | 2.8 | 60.0 | `20260911-213716-e62419` |

Zisková v **2 z 5** okien, obchodov spolu 14, break-even celkom 0.0737 %.

## Charakter

**Formácia / štruktúra** (istota slabá)

- len 14 obchodov — na zaradenie treba aspoň 20

- **Čo je normálne:** Zmes: časť obchodov sa chová ako prerazenie, časť ako návrat. Priemer preto o jednotlivom obchode nehovorí veľa.
- **Na čo pozor:** Práve pri tomto type sa najviac oplatí rozdeliť obchody na skupiny (`tester.analytics`) — priemer skrýva dve rôzne populácie.
- **Čo ladiť:** Podmienky vstupu (ktoré modely/formácie zapnuté) a potom až výstup.

Výstupy: `trailing_stop_loss` 57.1 %, `stop_loss` 35.7 %, `force_exit` 7.1 %

Čo z čísel vyplýva pre tento typ: [docs/TYPY_STRATEGII.md](../../../../docs/TYPY_STRATEGII.md).

## Ktorá skupina obchodov kazí výsledok

Na rozdelenie je málo obchodov — pusti viac behov alebo dlhšie okno.


## Je ten edge odlíšiteľný od náhody

Tá istá stratégia s náhodnými vstupmi — rovnako často, rovnakým smerom, s rovnakým SL/TP aj dĺžkou držania. Latka je edge **nad driftom trhu**, nie nad nulou.

| náhoda | break-even stratégie | break-even náhody | sigma | percentil |
|---|---|---|---|---|
| anytime (vstupy kedykoľvek v okne) | 0.0393 % | -0.0055 % ± 0.2479 | +0.18 | 60.8 |
| session (vstupy v tých istých hodinách, v akých obchoduje stratégia) | 0.0393 % | 0.0036 % ± 0.2580 | +0.14 | 59.8 |

Neodlisitelne od nahody (+0.2 sigma, percentil 60.8). Vyber vstupu k vysledku nepridava nic, co by sa nedalo dostat aj hodom mincou. POZOR: 14 obchodov je na tento test malo, rozdelenie nahody je siroke a rozdiel by musel byt velky, aby nieco znamenal.

## Slabne edge?

Posledné obdobie proti **vlastnej minulosti**: nie proti celkovému číslu (kratší úsek je prirodzene rozkolísanejší), ale proti rozdeleniu úsekov tej istej dĺžky, aké by tá istá stratégia vyrobila, keby sa edge nemenil.

| obdobie | obchodov | za mesiac | WR % | break-even % | percentil |
|---|---|---|---|---|---|
| 2022-10 - 2023-09 | 1 | 0.1 | 0.0 | -0.1107 | - |
| 2023-09 - 2024-08 | 2 | 0.2 | 100.0 | 0.7619 | - |
| 2024-08 - 2025-07 | 6 | 0.6 | 33.3 | 0.0397 | - |
| 2025-07 - 2026-06 | 5 | 0.5 | 60.0 | -0.0626 | - |

**MALO DAT** — celkom 14 obchodov, v poslednom období 5 — na rozlíšenie úpadku od bežného rozptylu treba aspoň 60 a 12. Pridaj okná alebo trhy.

## Interval okolo výsledku a čo to robí s účtom

Bootstrap po blokoch 2 obchodov, 10 000 opakovaní.

- break-even: namerané **0.0737 %**, medián 0.0696 %, 90 % interval -0.1568–0.3404 %
- P(edge > poplatok) = **54.6 %**
- max drawdown: medián 8.6 %, 95. percentil 18.3 %, najhorší 28.8 %
- najdlhšia séria strát: medián 3, 95. percentil 7 obchodov
- pravdepodobnosť ruiny účtu: 0.0 %
- aby 95 % ciest zostalo nad −20 %, riskuj najviac **227** na obchod pri účte 10 000

Bootstrap **nemeria pretrénovanie** — hovorí len o rozptyle vzorky. Proti pretrénovaniu chránia len okná, ktoré optimalizátor nevidel.

## Čo tu nie je

- **Iné trhy a timeframy.** Že myšlienka drží aj mimo trhu, na ktorom sa ladila, povie matica: `cli matrix --pairs all --timeframes 3m`.
- **Druhý engine.** Čísla sú z jedného enginu; signály sú v oboch rovnaké, fill model nie. Záver pre MultiCharts patrí emulátoru (`--engine multicharts`).
- **Hľadanie lepších parametrov.** Toto je fotka, nie ladenie — na to je `cli sweep` a `cli hyperopt`.

## Posudok (AI)

Chýba. Napíše ho AI: prečíta čísla vyššie a odpovie na týchto šesť otázok. Text patrí **medzi značky** nižšie, aby ho ďalší `cli checkup` preniesol ďalej.

1. **Na čo sa to hodí a na čo nie** — trh, timeframe, režim, veľkosť účtu; kde by to isté číslo znamenalo niečo iné.
2. **Má to potenciál?** Čo z čísel hovorí, že za tým je skutočný jav, a čo hovorí, že je to vlastnosť vzorky.
3. **Čo treba dorobiť** v samotnej stratégii — filtre, výstupy, sizing, sviatky a seansy, chýbajúce parametre.
4. **Čo otestovať ďalej** — konkrétne príkazy (`cli sweep`, `cli matrix`, `cli hyperopt`, druhý engine) a čo by ich výsledok rozhodol.
5. **Je to použiteľné, alebo je to o ničom?** Odpoveď má byť jednoznačná; „ešte uvidíme" je odpoveď len vtedy, keď je za ňou konkrétny test.
6. **Čo by som pridal** — nápad, ktorý v stratégii nie je a z týchto čísel dáva zmysel.
<!-- POSUDOK cisla=1f31d019 -->

1. **Na čo sa to hodí a na čo nie.** Toto je port naladeného stavu z roku 2022 (BTC 15m, futures s pákou), nie stratégia zmeraná dnes. Vo forme, v akej je, je to **veľmi zriedkavý filter**: 14 obchodov za päť rokov, v prvom okne (2021-22, medvedí trh) ani jeden. Hodí sa ako *doplnkový* signál na trendový trh s dlhšími nohami (2024-26 dala 11 z 14 obchodov), nie ako samostatný systém — pri 0,2 obchodu mesačne nemá čo živiť účet ani štatistiku. Na CFD bez burzového objemu (Dukascopy) tri z deviatich zapnutých indikátorov (OBV, CMF, MFI, CDV) merajú tickový objem klientov, takže tam by to isté číslo znamenalo iný signál.

2. **Má to potenciál?** Čísla to nerozhodnú: break-even 0,074 % je nad poplatkom, ale 90 % interval je −0,16 až +0,34 % a proti náhode je to +0,2 sigma. To nie je dôkaz edge ani jeho neprítomnosti — je to **nedostatok vzorky**. Za jav hovorí len jedno: tri z piatich okien sú ziskové a obchody sa zatvárajú prevažne trailingom (57 %), teda cena po vstupe naozaj išla smerom obchodu. Proti hovorí, že celý výsledok 2022-24 sú tri obchody. Skutočný jav (divergencia v smere trendu vyššieho TF) je v literatúre známy; čo tu treba overiť, je, či ho **zónový filter** neudusí — na 3 mesiacoch BTC bola medvedia zóna aktívna na 82 % barov aj po oprave, ktorá ráta len regulárne divergencie.

3. **Čo treba dorobiť.** (a) Zónový filter je hlavný dôvod malej vzorky; treba mu dať menej indikátorov alebo kratšie okno (`zoneWindow2 = 44` barov 4h je vyše týždňa) a zmerať, čo urobí s počtom obchodov. (b) Filter pullbacku na 15m je prísnejší než originál (ten rátal 5m bary vnútri baru) — pri behu na 5m grafe by to bol originál, treba to skúsiť. (c) Stop z 3 ATR je náhrada za pôvodný limit 200 $ pri pevnom stake; správna hodnota nie je zmeraná. (d) Rozbeh 3 408 barov je pre emulátor MultiCharts problém — prvé týždne okna dáva iné signály; emulátor by potreboval rozbeh pred oknom.

4. **Čo otestovať ďalej.** Najprv vzorku: `cli sweep --strategy divergence --param zoneWindow2=6:48:6 --goal break_even` a `cli sweep --param zoneFilter=false,true` — ak sa počet obchodov zdvihne na desiatky pri break-even nad poplatkom, oplatí sa pokračovať; ak edge zmizne s filtrom, filter bol celý výsledok. Potom `cli run --timeframe 5m` (originálny variant pullbacku) a `cli matrix --pairs all --timeframes 15m` (ETH — prahy sú v percentách a ATR, tabuľka neklame). `cli nulltest` až pri aspoň 60 obchodoch. Druhý engine: `--engine multicharts` na tom istom okne dal tri obchody na minútu rovnaké, rozdiel je len v rozbehu — to je overené.

5. **Je to použiteľné?** V tejto podobe **nie** — nie preto, že by prehrávalo, ale preto, že s 14 obchodmi za päť rokov sa nedá povedať nič a účet by čakal mesiace na jeden vstup. Použiteľné sa to stane až po bode 4: buď zónový filter povolí a vzorka narastie so zachovaným break-even, alebo sa ukáže, že bez filtra je to náhoda — obidve odpovede sú lepšie než dnešná.

6. **Čo by som pridal.** Vzdialenosť ceny od supertrendu 4h ako filter vstupu (v ATR): divergencia ďaleko pod čiarou trendu je iný obchod než tesne nad ňou, a práve výstup podľa trendu tu zatvára stratové obchody, takže vstup blízko čiary má malý priestor. A druhé: signál len z **počtu súhlasiacich indikátorov** (`minDivsLong` 2–3) namiesto zónového filtra — je to ten istý nápad („viac dôkazov"), ale na bare vstupu, nie z týždňa histórie vyššieho TF.

<!-- POSUDOK KONIEC -->
