# VALUE AREA REVERSION 1.0 — ako funguje

> V jednej vete: keď cena vypadne z value area včerajšieho profilu, ale predajcov ubúda (objem klesá) a do piatich sviečok ju silná sviečka s väčším objemom vráti späť dnu, stratégia kúpi so stopom pod dnom úniku a cieľom na hornej hrane value area (short naopak).

Zdroj: video LuxAlgo „I Turned A 4x World Cup Trader's Strategy Into An Indicator“ (youtube.com/watch?v=dUczefIYKIU),
stratégia Fabia Valentiniho (viacnásobné top 3 v Robbins World Cup Trading Championship).

## Ako vznikne obchod (long; short zrkadlovo nad VAH)
1. **Profil** — objem obchodovaný na každej cene počas seansy 18:00–18:00 New York. **Value area** je pásmo okolo
   najobchodovanejšej ceny (POC), kde prebehlo 70 % objemu. Predvolene sa berie profil **predošlej** seansy (vo videu čistejšie).
2. **Únik** — sviečka zavrie pod spodnou hranou value area (VAL).
3. **Slabnúci objem** — ďalšie medvedie sviečky pod VAL majú menší objem: predajcovia cenu nenasledujú, kupujúci ich absorbujú.
4. **Návrat** — do 5 sviečok od úniku zavrie býčia sviečka späť vo value area a má väčší objem ako posledná medvedia sviečka úniku.
   Voliteľne musí pohltiť telo predošlej sviečky.
5. **Vstup** — market na zavretí sviečky návratu. Kým beží obchod, ďalšie signály sa neberú.

## Stop a cieľ
- **Stop** pod najnižším low úniku (+ voliteľná rezerva).
- **Cieľ** horná hrana value area (VAH). Voliteľne POC alebo násobok stopu.

## Slovníček
- **Volume profile** — koľko sa obchodovalo na ktorej cene.
- **POC** — cena s najväčším objemom. **VAH / VAL** — horná a spodná hrana value area.
- **Medvedí / býčí objem** — objem medvedej / býčej sviečky (graf nevidí, kto bol agresor; je to priblíženie ako vo videu).
