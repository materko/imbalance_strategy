# Big 7 + SOXX — čo je čo na paneli

Vysvetlivky ku [big7_basket_ema.pine](big7_basket_ema.pine). Ladené na **čierne pozadie**.

## Čo panel kreslí

| prvok | vzhľad | čo znamená |
|---|---|---|
| **Plocha pod čiarou** | zelená hore, červená dole | smer. Sýta = skóre je za prahom (presvedčivé), bledá = skóre je medzi nulou a prahom (slabé) |
| **Hrubá čiara** | 3 px, zelená / červená | samotné skóre smeru, −100 až +100 |
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

Zoradená tak, že **to najdôležitejšie je hore**. V nízkom paneli sa tabuľka odrezáva zdola,
takže smer, skóre a šírka prežijú aj vtedy, keď na tickery už miesto nezostane.

| riadok | čo je to |
|---|---|
| **SMER** | výsledok, celý riadok na farebnom pozadí: `LONG` / `SELL` / `BEZ SMERU` / `MIMO HODÍN` |
| **skóre** | číslo −100…+100, veľkým písmom, vo farbe smeru |
| **šírka** | `koľko je hore / koľko má dáta`. Zelené, keď je splnené `Min. titulov na strane signálu` |
| KÔŠ | vážený priemer siedmich titulov |
| SOXX | polovodiče |
| QQQ | index na porovnanie |
| sedem tickerov | percentuálna zmena každého titulu |

**Tabuľka — rozsah** určuje, koľko riadkov sa kreslí. Na nízkom paneli (mobil, malý panel
pod grafom) sa tabuľka odrezáva zdola, tak si vyber podľa miesta:

| rozsah | riadkov | čo obsahuje |
|---|---|---|
| Len smer | 1 | `SMER` a nič viac |
| Kompaktná | 3 | + skóre a šírka |
| **Stredná** (predvolené) | 6 | + kôš, SOXX, index |
| Plná | 13 | + všetkých sedem titulov |

Kam sa tabuľka postaví, nastavíš v *Tabuľka — kde* (štyri rohy panelu).

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

## Hlavička panelu

V hlavičke je jediná hodnota — **skóre**. Všetky ostatné čiary a značky sú `display.pane`,
teda kreslia sa, ale do hlavičky nelezú, takže tam neostávajú prázdne `∅`.

Dlhý zoznam vstupov za názvom (`9 1 1 1 1 0.5 …`) je TradingView, nie skript. Vypneš ho:
pravým na panel → **Settings → Status line → Arguments**.
