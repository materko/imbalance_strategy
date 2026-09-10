# Zadanie: stratégia na tržnej štruktúre (BOS / CHoCH)

Toto je pracovné zadanie pre samostatné sedenie. Je úmyselne úplné — čítať sa má samo,
bez toho, aby si musel dohľadávať kontext v inom okne.

## Prečo to staviame

Tri dôvody, každý sám o sebe by nestačil:

1. **Rámec má byť generický, a to sa dá overiť len druhou skutočnou stratégiou.** Dnes je
   v registry IBS a ukážkové `demo_breakout`. Keď sa pri písaní tejto stratégie ukáže, že
   `tradebot/core` alebo adaptér potrebuje vedieť jej meno, je to chyba návrhu jadra —
   a chceme to vedieť.
2. **Je to iný archetyp než IBS.** IBS je prerazenie (breakout) v NY seanse. Štruktúrna
   stratégia môže byť protitrendová (odber likvidity). Dve nekorelované stratégie sú
   jediná cesta, ako z `tester.portfolio` dostať niečo lepšie než „jeden beh s väčšou
   pozíciou".
3. **Štruktúra sa dá definovať objektívne, a preto testovať.** Celý svet ICT/SMC ju kreslí
   od oka — desať traderov ju uvidí desaťkrát inak. Keď je definovaná pravidlom, dá sa
   zmerať, či na nej niečo je. (Mimochodom to nie je vynález ICT: Wyckoff aj Gann merali
   presne tie isté swingy.)

## Čo presne je štruktúra

Definície musia byť také, aby ich vedel dvakrát nezávisle naprogramovať dvoch ľudí a vyšlo
im to isté. Nič „vyzerá to ako".

**Swing high** je bar, ktorého `high` je vyššie než `high` všetkých `L` barov vľavo
a všetkých `R` barov vpravo. **Swing low** symetricky s `low`.

> **Toto je najdôležitejšia veta celého zadania.** Swing sa dá **potvrdiť až `R` barov
> potom, čo nastal**. Engine ho pred tým nesmie použiť ani na kreslenie, ani na
> rozhodnutie. Väčšina štruktúrnych stratégií na internete tu podvádza a preto vyzerá
> skvelo v backteste — my na to máme test (nižšie).

Štruktúra má **stav**: `bullish` alebo `bearish`. Začína neutrálne, prvý potvrdený prielom
ju nastaví.

| udalosť | kedy nastane | čo urobí so stavom |
|---|---|---|
| **BOS** (break of structure) | v stave `bullish` sa bar **zavrie** nad posledným potvrdeným swing high (v `bearish` pod swing low) | stav ostáva, posúva sa referenčná úroveň |
| **CHoCH** (change of character) | v stave `bullish` sa bar **zavrie** pod posledným potvrdeným swing low (v `bearish` nad swing high) | stav sa otočí |

Rozhoduje **zatvorenie baru**, nie dotyk knôtom — knôt je ten istý spor „vidím / nevidím",
akému sa vyhýbame.

## Čo má stratégia obchodovať

Vstup je **prepínač**, nie tri stratégie. Všetky tri varianty stoja na tej istej štruktúre,
takže patria do jedného enginu a porovnajú sa sweepom:

| `entryMode` | vstup | myšlienka |
|---|---|---|
| `choch` | v smere **novej** štruktúry, na zatvorení baru, ktorý CHoCH spôsobil | otočenie trendu |
| `bos` | v smere pokračovania po BOS | trend pokračuje |
| `sweep` | **proti** CHoCH — CHoCH nadol znamená long | falošné prerazenie / odber likvidity |

`sweep` vyzerá na prvý pohľad nezmyselne a je to práve ten variant, ktorý v podkladovom
videu vychádzal najlepšie (na EURUSD a zlate). Nech ho meria mriežka, nie názor.

### Výstupy — jeden z nich je nová vec

- **SL**: za posledný potvrdený swing v protismere, plus rezerva (`slBuffer` v `atr`), alebo
  násobok ATR — prepínačom.
- **TP**: násobok rizika (`rrRatio`), **alebo na ďalšej štruktúrnej udalosti** v smere
  obchodu (`exitMode = structure`).
- **Časový limit** v baroch (`maxBars`), ako má IBS.

**Výstup na štruktúrnej udalosti engine dnes nevie** — vie SL, TP a čas. Je to teda nová
rodina výstupov a treba ju spraviť **v engine stratégie**, nie v jadre. Keby si musel
siahnuť do `tradebot/core`, zastav sa a napíš prečo; pravdepodobne sa to dá inak.

## Parametre

Prahy **nikdy v absolútnych bodoch** — `atr` alebo `pct`. Prah v bodoch funguje presne na
jednom trhu a matica trhov ho aj tak prepočíta.

| parameter | typ | rozsah | čo robí |
|---|---|---|---|
| `swingLeft`, `swingRight` | int | 2–20 | koľko barov vľavo/vpravo definuje swing |
| `entryMode` | enum | `choch` / `bos` / `sweep` | ktorý variant vstupu |
| `exitMode` | enum | `rr` / `structure` | pevné RR, alebo ďalšia udalosť štruktúry |
| `rrRatio` | float | 1–8 | pomer TP k SL pri `exitMode = rr` |
| `slMode` | enum | `swing` / `atr` | odkiaľ sa berie stop |
| `slBuffer` | size (`atr`) | 0–1 | rezerva za swing |
| `slAtrMult` | float | 0.5–5 | násobok ATR pri `slMode = atr` |
| `minSwingSize` | size (`atr`) | 0–3 | swing menší než toto sa ignoruje (šum) |
| `maxBars` | int | 0–500 | 0 = bez časového limitu |
| `tradeDirection` | enum | Long only / Short only / Both | ako v IBS |
| `useSession` | bool + hodiny | — | voliteľné okno; **default vypnuté** |

Sizing musí byť **risk-based** (pole s dolárovým rizikom, `risk_field` v `StrategySpec`),
nie pevný počet kontraktov — inak sa výsledok nedá prepočítať na iný účet a Monte Carlo
nedá odporúčanie k riziku.

## Kde čo patrí

Presný postup je v [docs/STRATEGIE.md](../STRATEGIE.md) — **prečítaj si ho celý, toto ho
nenahrádza.** Ako živý vzor slúži `tradebot/strategies/demo_breakout/`: je to najmenšia
úplná stratégia v repozitári, má všetko od Pine zdroja po posudok.

```
tradebot/strategies/structure/
    __init__.py      SPEC = StrategySpec(...)
    config.py        parametre, CONSTRAINTS, SIZE_FIELDS, ENUM_FIELDS
    engine.py        celá logika (swingy, BOS/CHoCH, vstupy, výstupy)
    drawing.py       kresby: swingy, úrovne, BOS/CHoCH značky, SL/TP boxy
    meta.py          vrstvy grafu, titulky druhov kresieb, závislosti prepínačov
    freqtrade.py     trieda pre Freqtrade adaptér
    multicharts.py   trieda pre MultiCharts adaptér
    hyperopt.py      StrategyHyperopt: odporúčané rozsahy, väzby, varovania
    configs/         aspoň jeden profil (default)
    docs/sources/    Pine zdroj
    docs/ANALYTIKA.md (vygeneruje `cli checkup`)
```

Plus jeden riadok v `tradebot/strategies/__init__.py`.

**Pine zdroj je povinný**, nie voliteľný: `test_registry.py::test_pine_source_and_engine`
ho vyžaduje a je to celá myšlienka repozitára — tá istá stratégia musí ísť skontrolovať
na TradingView. Napíš teda aj `.pine` a drž ho v zhode s configom (`test_pine_parity.py`
to stráži).

## Kedy je hotová

Checklist z [STRATEGIE.md](../STRATEGIE.md) platí celý:

| # | čo | ako to overiť |
|---|---|---|
| 1 | balík, registry, shim, šablóna | `pytest tradebot/tests/test_registry.py` |
| 2 | config sedí s Pine | `pytest tester/tests/test_pine_parity.py` |
| 3 | logika enginu | vlastný test na syntetických baroch |
| 4 | nič nerozbité | `pytest -q` |
| 5 | beží vo Freqtrade | `cli run --strategy structure --engine freqtrade …` |
| 6 | beží v MultiCharts | `cli run --strategy structure --engine multicharts …` |
| 7 | analytika | `cli checkup --strategy structure …` |
| 8 | posudok | šesť otázok zodpovedaných v tom istom dokumente |

K tomu tri veci navyše, ktoré sú **špecificky pre túto stratégiu** dôležité:

**9. Test na potvrdenie swingu.** Syntetické bary, kde swing high nastane a hneď potom
cena spadne. Engine nesmie ten swing použiť skôr než `swingRight` barov po ňom — ani na
vstup, ani na SL, ani na kresbu. Bez tohto testu sa nedá tvrdiť, že stratégia nepozerá
dopredu, a všetko ostatné je potom bezcenné.

**10. Syntetický trh.** `cli run --strategy structure --pair SYNTH/USDT:USDT` na piatich
referenčných oknách. Na premiešanom trhu má vyjsť **nula**. Keby tam štruktúrna stratégia
zarábala, znamená to, že „štruktúra" v nej je len tvar barov a nie správanie účastníkov —
a to je nález, ktorý treba napísať skôr, než sa čokoľvek ladí. Podrobne
[AI_TESTING.md §8j](../../tester/AI_TESTING.md).

**11. Matica trhov.** `cli matrix --strategy structure --pairs all --timeframes 3m`.
Štruktúra je tvrdenie o tom, ako sa trhy chovajú — ak platí, má platiť na viacerých.

## Poradie práce

Nie je to ľubovoľné; každý krok stojí na predošlom:

1. **Definície a engine na syntetických baroch.** Najprv swingy s potvrdením, potom stav
   štruktúry, potom udalosti. Testy píš spolu s tým, nie potom.
2. **Kresby.** Bez nich sa nedá pozrieť, či to, čo engine vidí, je to isté, čo vidíš ty na
   grafe — a to je jediný spôsob, ako chytiť tichú chybu v definícii.
3. **Registry, adaptéry, profil.** Až teraz `pytest -q` musí byť zelený.
4. **Prvý beh na jednom okne**, pozri graf, over pár obchodov ručne.
5. **Päť referenčných okien + syntetický trh + matica.** Až tu sa dá povedať, či za tým
   niečo je.
6. **`cli checkup` a posudok.** Až potom ladenie — hyperopt na stratégii, o ktorej nevieme,
   či je odlíšiteľná od náhody, nájde presne to, čo v tom okne bolo.

## Čo nerobiť

- **Nesiahaj do `tradebot/core` kvôli tejto stratégii.** Keď jadro potrebuje vedieť jej
  meno, chýbajúca informácia patrí do `StrategySpec`.
- **Neladiť pred analytikou.** Poradie je: funguje → je odlíšiteľné od náhody → až potom
  hyperopt.
- **Nepoužiť swing skôr, než je potvrdený.** Viď bod 9.
- **Žiadne prahy v bodoch.** `atr` alebo `pct`.
- **Nerobiť závery z jedného okna.** Päť referenčných okien a znamienko po rokoch, nie súčet.
- **Nepridávať parametre „pre istotu".** Každý parameter je ďalší stupeň voľnosti, ktorý
  hyperopt využije na preoptimalizovanie. Keď parameter nemá dôvod, nech tam nie je.

## Čo od toho čakať

Pravdepodobne to nebude zázrak — a to je v poriadku. Užitočné výsledky sú tri a všetky sa
rátajú:

- Stratégia **funguje** a je nekorelovaná s IBS → portfólio má konečne dvoch skutočných
  členov.
- Stratégia **nefunguje** a vieme povedať prečo (napr. `sweep` áno a `bos` nie) → to je
  zistenie o trhu, ktoré platí aj pre IBS.
- Rámec sa pri jej písaní **niekde zadrhne** → oprava jadra, ktorá pomôže každej ďalšej.

Neúspech je len jeden: stratégia, o ktorej sa po týždni nedá povedať ani jedno z toho.
