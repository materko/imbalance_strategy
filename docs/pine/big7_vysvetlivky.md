# Big 7 + SOXX — čo je čo na paneli

Vysvetlivky ku [big7_basket_ema.pine](big7_basket_ema.pine). Ladené na **čierne pozadie**.

## Čo panel kreslí

| prvok | vzhľad | čo znamená |
|---|---|---|
| **Plocha pod čiarou** | zelená hore, červená dole | smer. Sýta = skóre je za prahom (presvedčivé), bledá = skóre je medzi nulou a prahom (slabé) |
| **Hrubá čiara** | 3 px, zelená / červená | samotné skóre smeru, −100 až +100 |
| **Tenká sivá čiara** | 1 px | referencia: v režime *Skóre* je to skóre **bez vyhladenia**, v režime *Percentá* je to **EMA koša**. Keď sa hrubá čiara odtrhne od tenkej, pohyb práve zrýchľuje |
| **Dve prerušované čiary** | zelená hore, červená dole | prahy `±Prah skóre`. Za nimi vzniká signál |
| **Vodorovná čiara v strede** | sivomodrá | nula |
| **Pásik štvorčekov pri spodnej hrane** | zelené / červené | aktuálny stav bar po bare. Prázdne miesto = bez smeru |
| **Podfarbené pozadie** | slabo zelené / červené | ten istý stav, len periférnym videním. Vypína sa v *Podfarbiť pozadie podľa stavu* |
| **Tmavosivé pozadie** | šedé | mimo 9:30–16:00 New York. Vtedy sú akciové feedy stojaté a nesignalizuje sa |
| **Štítok LONG / SELL** | zelený / červený, na čiare | okamih **otočenia** stavu. Nie je to „stále platí", je to „práve teraz sa to zmenilo" |
| **Veľká visačka vpravo** | na konci čiary | aktuálny stav: `LONG`, `SELL`, `BEZ SMERU` alebo `MIMO HODÍN` |
| **▲ oranžový trojuholník** | pri hornej hrane | úzky ťah: kôš letí, ale index stojí, alebo šírka nesúhlasí |
| **◆ fialový kosoštvorec** | pri hornej hrane | polovodiče idú proti košu |

## Tabuľka vpravo hore

| riadok | čo je to |
|---|---|
| sedem tickerov | percentuálna zmena každého titulu od denného ukotvenia |
| **KÔŠ** | vážený priemer tých siedmich (zvýraznený riadok) |
| SOXX | polovodiče |
| QQQ | index na porovnanie |
| šírka | `koľko je hore / koľko má dáta`. Zelené, keď je splnené `Min. titulov na strane signálu` |
| skóre | číslo −100…+100, veľkým písmom, vo farbe smeru |
| **smer** | výsledok s farebným pozadím: LONG / SELL / BEZ SMERU / MIMO HODÍN |

## Zložky skóre (zapína sa v *Kresliť zložky skóre*)

Štyri tenké čiary v mierke skóre. Ukážu, ktorá zložka skóre ťahá a ktorá mu odporuje.

| farba | zložka |
|---|---|
| žltá, schodíková | **šírka** — koľko zo siedmich je na tej istej strane |
| fialová | **SOXX** |
| oranžová | **vedenie** — o koľko kôš prekonáva index |
| zelenkavá | **trend** — sklon EMA nad košom |

Piata zložka (kôš) je samotná hlavná čiara v režime *Percentá koša*.

## Dva režimy

Prepína sa v *Čo kresliť*. Skóre a percentá majú úplne inú mierku, preto sa nekreslia naraz —
do Data Window však ide vždy oboje.

- **Skóre smeru** (−100…+100) — hlavný pohľad, toto sleduj
- **Percentá koša** (%) — kôš a jeho EMA, keď chceš vidieť surové čísla

## Prečo v legende svietia prázdne ∅

Vypnuté čiary (napr. zložky skóre) tam ostávajú ako `∅`. Skryješ ich: pravým na panel →
**Settings → Status line → Indicator values**.
