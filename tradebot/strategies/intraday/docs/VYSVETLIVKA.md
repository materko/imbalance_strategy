# INTRADAY 1.0 — ako funguje

> V jednej vete: stratégia ide zhora nadol ako Martinova smernica — určí smer dňa, počká, kým trh zoberie likviditu predošlého dňa v protismere, a vstúpi limitkou v malej 5m zóne, ktorá leží v 15m zóne a tá v silnej 1H zóne.

## Ako vznikne obchod
1. **Daily bias** — smer dňa: včerajšie zavretie Nasdaqu nad 20-dňovým priemerom = long, pod ním = short (dá sa prepnúť na „včera vs predvčerom“ alebo vypnúť).
2. **Likvidita v protismere** — pri long biase „hľadáme nižšiu likviditu“: zóna na vstup musí ležať pri alebo pod **low predošlého dňa (PDL)**, kde sú stopky. Cena na ceste do zóny tieto stopky vyberie a limitka sa vyplní práve tam. Pri short biase zrkadlovo s high (PDH). Prepínač „sweep“ namiesto toho čaká, kým už bolo PDL/PDH zobraté.
3. **1H zóna** — miesto, kde sa cena krátko zastavila (báza) a potom silno odišla (aspoň 1,5 ATR). Demand pre long, supply pre short.
4. **15m zóna v 1H zóne**, potom **5m zóna v 15m zóne** — ten istý obrazec na menšom grafe, ktorý leží vnútri väčšej zóny. Zóna je tak užšia a stop menší.
5. **Vstup** — limitka na hranu 5m zóny (dotyk), len počas NY seansy 9:30–16:00, najviac 2 obchody denne. Zóna sa použije len raz.

## Stop a cieľ
- Stop za vzdialenejšiu hranu zóny (+ malá rezerva), cieľ 2× stop. Voliteľne cieľ na opačnú likviditu (PDH pri longu).
- Bez trailingu a bez zatvárania na konci seansy (pravidlá testovania).

## Slovníček
- **Supply / demand zóna** — cenové pásmo, odkiaľ cena silno odišla; pri návrate tam často čakajú nevyplnené príkazy.
- **Proximal / distal** — bližšia hrana zóny (tam sa vstupuje) a vzdialenejšia (za ňou je stop).
- **PDH / PDL** — high / low predošlého dňa.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe.
