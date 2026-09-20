# Projekt ORB — nastavenie a optimalizácia

Ten istý postup, akým sme ladili IBS: systematické sweepy, výsledky v R, overenie na
piatich oknách a až potom prop simulácia.

**Stav k 18. 9. 2026:** na PC1 (Mac mini) prebehlo **13 745 pokusov**, výsledky sú
v `prehlad/vysledky_PC1_13745pokusov.md`. Tu je zhrnutie a plán, čo ďalej.

---

## Čo už vieme

### Dve metodické opravy, ktoré znehodnotili staršie čísla

**1. Metrika je R, nie percentá účtu.** Backtester nevie otvoriť menej ako 1 kontrakt na
MNQ ani na zlate, takže zadané riziko 100 $ sa nedodržalo — reálne bolo na zlate priemerne
1 700 $ a na MNQ 236 $. Nastavenie so širokým stopom tým otváralo väčšiu pozíciu a v
dolároch vyzeralo lepšie, hoci edge malo rovnaký alebo horší. Na BTC sizing funguje
správne (dá sa obchodovať zlomok kontraktu).

**2. `minSlDistance` musí byť zapnuté.** Štandardne je 0 a to robilo veľkú škodu: pri
stope `break_candle` na 2m BTC vedel stop pristáť 0,6 bodu od vstupu pri cene 110 000, čo
dalo jednému obchodu R = 539. Na behu s 1 935 obchodmi držalo **1,8 % obchodov viac R, než
bol celý zisk** — bez nich bola tá istá konfigurácia stratová.

Teraz je `minSlDistance = 0,2 %` natvrdo a R každého obchodu sa oreže na 10.

### Ako čítať tabuľky

- **na obchod** (expectancy v R) — ale poradie sa určuje podľa **spodnej hranice
  spoľahlivosti**, aby vzorka so 150 obchodmi neprebila vzorku s 300 len šťastím
- **PF** pod 1,2 nestojí za nič
- **max pokles** v R — pomer zisku k nemu je dôležitejší než samotný zisk
- **winrate pri ORB sedí okolo 35–50 %** a sám o sebe nič nehovorí, lebo RRR je 1,5–3
- Nastavenia pod **150 obchodov za rok** sa nezobrazujú — pri 60–100 obchodoch vychádzali
  expectancy až 1,0 R, pri 400+ najviac 0,07 R

---

## Najlepšie doteraz (posledný rok, v R)

| Trh | TF | Seansa | Vstup | RRR | SL | Obch. | WR | PF | Na obchod | Max pokles |
|---|---|---|---|---|---|---|---|---|---|---|
| **MNQ** | 15m | both | close | 2,0 | atr | 417 | 32,1 % | 1,599 | **0,405 R** | 19,25 R |
| **XAU** | 30m | london | close | 3,0 | atr | 167 | 49,1 % | 1,779 | **0,380 R** | 6,67 R |
| **BTC** | 3m | london | close | 1,5 | break_candle | 270 | 33,3 % | 2,137 | **0,758 R** | 12,0 R |

Všetky zatvárajú pozíciu na konci seansy; nič nedrží cez noc.

**Pozorovanie:** na zlate aj BTC vyhráva **londýnska** seansa, na MNQ obe. Vstup `close`
vyhráva všade — ale `stop`, ktorý by bol pri ORB prirodzenejší, sa zatiaľ **nedá otestovať**
(viď nižšie).

---

## Známe obmedzenia

**~~Chyba: `entryMode = stop` vždy spadne~~ — OPRAVENÉ 18. 9. 2026** (commit `afe4b1d9`).
Doplnené `OrderType.STOP` a jeho vyplnenie v emulátore: stop je zrkadlo limitky — čaká na
*prienik* úrovne, nie na *návrat* k nej. Overené na XAU 15m: `stop` dal 142 obchodov
namiesto pádu (`close` 141, `retest` 33).

**Dôsledok:** nočný beh na PC1 testoval len `close` a `retest`, takže **poradie víťazov
môže byť iné**. Pri ORB je vstup na prerazení prirodzenejší. Popis pôvodnej chyby ostáva
v [`CHYBA_entryMode_stop.md`](CHYBA_entryMode_stop.md).

**`maxTradesPerDay` je limit na seansu, nie na deň.** Pri `both` je denný strop dvojnásobný.

**Časť parametrov engine v danom režime nečíta:** `rrRatio` len pri cieli `rr`, `tpAtrMult`
len pri `atr`, `slAtrMult` len pri stope `atr`, `retestMaxBars` len pri vstupe `retest`.
Dĺžka rangu pripúšťa len 15, 30 a 60 minút.

---

## Plán — čo ďalej

- [ ] **Overiť najlepšie tri na piatich referenčných oknách** (`cli checkup`). Doteraz je
      všetko merané len na poslednom roku — to je presne tá diera, ktorá nás pri IBS
      zakaždým dobehla.
- [x] ~~Rozhodnúť o chybe `stop`~~ — **opravené 18. 9.**, doplnený `OrderType.STOP`
- [ ] **Zopakovať ladenie s `entryMode = stop`** — teraz sa dá otestovať tretí režim vstupu
- [ ] **Prop simulácia** pre najlepšie nastavenia (FTMO 100k) — koľko výplat, koľko
      spálených účtov, za ako dlho.
- [ ] **Test odolnosti:** nulltest (odlíšiteľné od náhody?), decay (neslabne edge?),
      matica na ďalších trhoch.
- [ ] **Rozdelenie obchodov** — ktorá skupina kazí výsledok (deň v týždni, hodina,
      veľkosť rangu).

---

## Čo je v tomto priečinku

| | |
|---|---|
| `prehlad/kandidati.md` | **top 10 podľa pomeru zisk/pokles — s týmito sa pracuje ďalej** |
| `prehlad/vitazi_PC1.md` | presné nastavenia víťaza pre každý trh |
| `prehlad/vysledky_PC1_13745pokusov.md` | tabuľky najlepších nastavení pre každý trh |
| `prehlad/metodika_a_zistenia.md` | pôvodný popis metodiky z PC1 (ako čítať čísla) |
| `nastavenia/najlepsie_PC1.json` | presné parametre víťazov z nočného behu |
| `nastavenia/*.json` | deväť ORB profilov, ktoré sú aj vo webapp |
| `CHYBA_entryMode_stop.md` | popis chyby a možnosti riešenia |
| `behy/` | zatiaľ prázdne — sem pôjdu detaily vybraných backtestov |

V histórii webapp je **394 ORB behov**.
