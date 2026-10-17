# Silver Bullet 1.0 (ICT) — ako funguje

> V jednej vete: medzi 10:00 a 11:00 New York počká, kým cena vyberie skoršie dno alebo vrchol dňa (sweep), potom kým prudký pohyb opačným smerom zanechá FVG, a vstúpi limitkou na tom FVG so stopom za sweepom a cieľom na protiľahlej likvidite.

## Ako vznikne obchod (long; short zrkadlovo)
1. **Okno** — obchoduje sa len v čase 10:00–11:00 New York (15:00–16:00 u nás v lete). Mimo okna sa nič nezačína.
2. **Likvidita** — skoršie dná dňa: najnižšie dno od 8:00 do 10:00 a dná grafu (swingy) od 8:00. Pod nimi ležia stopky (sell-side likvidita).
3. **Sweep** — v okne cena knôtom prerazí také dno a zoberie stopky („earlier low“). Kým ide nižšie, extrém sweepu sa posúva.
4. **FVG** — po sweepe príde prudký pohyb hore a zanechá fair value gap: medzeru medzi 1. a 3. sviečkou, aspoň 0,1 ATR, najviac 10 barov po extréme sweepu. Voliteľne treba aj zlom štruktúry (MSS).
5. **Vstup** — limitka na hornom okraji FVG (pri shorte na spodnom), alebo voliteľne na jeho strede. Platí do 11:00; ak cena medzitým spadne pod extrém sweepu alebo dosiahne cieľ bez nás, setup sa zruší.
   Predvolene jeden obchod za deň.

## Stop a cieľ
- **Stop** pod extrémom sweepu (+ malá rezerva v ATR). Voliteľne sa obchod vynechá, keď je stop príliš široký.
- **Cieľ** na protiľahlej likvidite: najbližší skorší vrchol nad vstupom („TARGET“), ktorý je aspoň 1 R od vstupu. Keď taký nie je, obchod sa nerobí. Prepnúť sa dá na pevný násobok stopu (RR).
- Bez trailingu a bez zatvárania na konci seansy (výstup v čase sa dá zapnúť).

## Slovníček
- **Silver Bullet** — model ICT (Inner Circle Trader) na jedno okno dňa, keď sa často hýbe po vybratí likvidity.
- **Likvidita (BSL / SSL)** — miesto, kde ležia stopky: nad vrcholmi (buy-side) a pod dnami (sell-side).
- **Sweep** — cena krátko prerazí úroveň, zoberie stopky a otočí sa.
- **FVG** — fair value gap, nevyplnená medzera po prudkom pohybe.
- **MSS** — market structure shift: zavretie za posledný swing pred sweepom.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe.
