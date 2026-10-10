# SWEEP FVG 1.0 — ako funguje

> V jednej vete: stratégia počká, kým trh vyberie likviditu (stopky nad vrcholom alebo pod dnom), potom kým sa štruktúra zlomí opačným smerom (CHoCH alebo BOS), a vstúpi limitkou na okraji najbližšieho FVG, ktorý ten pohyb zanechal.

## Ako vznikne obchod (short; long zrkadlovo)
1. **Likvidita** — výrazný vrchol na 15m alebo 1h grafe. Nad ním ležia stopky (buy-side likvidita, BSL). Rovnaké vrcholy sa zlúčia do jednej silnejšej úrovne.
2. **Výber likvidity** — cena prerazí vrchol a zoberie stopky. Kým ide vyššie, extrém výberu sa posúva.
3. **CHoCH / BOS** — do 30 barov sviečka zavrie pod posledné dno pred extrémom výberu. Ak trh dovtedy rástol, je to CHoCH (zmena charakteru), inak BOS (pokračovanie). Prepínač vie brať len jeden z nich.
4. **FVG** — medzera medzi 1. a 3. sviečkou (cena tadiaľ prešla len jedným smerom), aspoň 0,3 ATR, ktorá vznikla v pohybe od extrému výberu po zlom. Berie sa najbližšia k cene, ku ktorej sa cena ešte nevrátila.
5. **Vstup** — limitka na spodnom okraji FVG (pri longu na hornom). Čaká najviac 20 barov po zlome (nastaviteľné), predvolene na 5m grafe.
   Ak cena medzitým vyjde nad extrém výberu alebo dosiahne cieľ bez nás, setup sa zruší.

## Stop a cieľ
- **Stop** nad extrémom výberu likvidity (+ malá rezerva v ATR). Voliteľne sa obchod vynechá, keď je stop príliš široký.
- **Cieľ** nastaviteľný: násobok stopu (predvolene 2×), pevný počet bodov, alebo najbližšia nevybratá likvidita v smere obchodu.
- Bez trailingu a bez zatvárania na konci seansy (dá sa zapnúť zatvorenie v čase).

## Slovníček
- **Likvidita (BSL / SSL)** — miesto, kde ležia stopky: nad vrcholmi (buy-side) a pod dnami (sell-side).
- **CHoCH** — change of character: prvý zlom štruktúry proti doterajšiemu smeru.
- **BOS** — break of structure: zlom v smere doterajšej štruktúry.
- **FVG** — fair value gap, nevyplnená medzera po prudkom pohybe.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe.
