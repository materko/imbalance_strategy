# NB 1.0 — ako funguje

> V jednej vete: keď je trh na štvorhodinovom grafe v trende a na 15-minútovom chvíľu stojí na mieste, vstúpi sa stop orderom hneď, ako cena z tohto miesta vyrazí v smere trendu.

Podľa videa TradeCZ s traderkou Nikolou (YouTube KBCvpjMWd5A), zadanie 28. 10. 2026.

## Trend
- Na vyššom TF (default H4) sa počíta **SMA 10 a SMA 20** zo zavretí. Uptrend znamená, že rýchla je nad pomalou a sviečka zavrela nad rýchlou. Vtedy sa berú len longy. Pri downtrende zrkadlovo len shorty.
- Aj na grafe (M15) musí byť pri longu zavretie nad oboma SMA a rýchla nad pomalou. Nikola to hovorí takto: „SMA ti ukážu smer“, preto prieraz proti nim neberie.

## Konsolidácia a vstup
- **Konsolidácia** je posledných 8 sviečok grafu (vrátane knôtov) v pásme širokom najviac 2 ATR. Trh v nej nemá smer.
- **Vstup:** stop order 1 tick nad hornou hranou (long) alebo pod dolnou (short). Vstupuje sa hneď pri prieraze, nečaká sa na zavretie sviečky. Keď sa hranice konsolidácie zmenia, order sa preloží.
- **Okno:** vstupuje sa len 2:00–16:00 New York (8:00–22:00 SK). Dni v týždni sa dajú vypnúť, Nikole sa najlepšie darí v pondelok až stredu.

## Stop a cieľ
- **Stop** je za opačnou hranou konsolidácie + rezerva (0,25 ATR, u Nikoly 5 pipov) + 1 tick. **Cieľ** je 3 × riziko.
- **Miesto do cieľa:** keď je najbližší vrchol (pri longu) alebo dno (pri shorte) vyššieho TF bližšie než 2,5 R od vstupu, obchod sa vynechá, lebo cieľ by bol za prekážkou.

## Slovníček
- **SMA** — jednoduchý kĺzavý priemer zavretí; SMA 10 = priemer posledných 10 sviečok.
- **Konsolidácia** — úsek, keď cena kmitá v úzkom pásme bez smeru.
- **Stop order** — príkaz, ktorý sa vyplní až keď cena prejde zadanú úroveň.
- **R** — riziko obchodu (vzdialenosť vstupu od stopu); cieľ 3 R = trikrát ďalej ako stop.
- **ATR** — priemerný rozsah sviečky; prahy v ATR sedia na pokojnom aj rušnom trhu.
