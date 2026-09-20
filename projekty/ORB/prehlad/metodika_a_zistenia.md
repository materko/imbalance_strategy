# ORB — výsledky testov

Priečinok sa plní automaticky počas behu testov na PC1 (Mac mini) a synchronizuje sa do iCloudu,
takže je dostupný aj z MacBooku.

Posledná zmena: 17. 9. 2026

## Dôležité: metrika sa zmenila

Staršie tabuľky v tomto priečinku uvádzali zisk ako **percento účtu** a tvrdili, že sa to rovná
zisku v R. Nerovná. Tie čísla sú zahodené.

Backtester nevie otvoriť menej ako 1 kontrakt na MNQ ani na zlate, takže zadané riziko 100 $
na obchod sa v skutočnosti nedodrží — reálne riziko bolo na zlate v priemere 1 700 $ na obchod
a na MNQ 236 $. Nastavenie so širokým stopom tým pádom otváralo väčšiu pozíciu, zarobilo viac
dolárov a vo výsledkoch vyzeralo lepšie, hoci jeho edge bol rovnaký alebo horší. Na BTC sizing
funguje správne, lebo sa dá obchodovať zlomok kontraktu.

**Všetko sa teraz počíta v R** — v násobkoch rizika konkrétneho obchodu, spočítaných z
jednotlivých obchodov:

    riziko = |vstup − pôvodný stop| × počet kontraktov × hodnota bodu
    R      = zisk obchodu / riziko

Takto sú čísla porovnateľné medzi trhmi. Po prepočte vyšli všetky tri trhy podobne (rádovo
desiatky R za posledný rok), nie 50-násobne odlišne, ako to vyzeralo predtým.

## Druhá oprava: minimálna vzdialenosť stopu

Parameter `minSlDistance` je štandardne **vypnutý** (0) a to robilo veľkú škodu. Pri režime
stopu `break_candle` na dvojminútovom grafe BTC vedel stop pristáť 0,6 bodu od vstupu — pri cene
110 000. Riziko na takom obchode vyšlo takmer nula, takže jeden jediný obchod dostal R = 539.

Na jednom behu s 1 935 obchodmi držalo 1,8 % obchodov **viac R, než bol celý zisk behu**. Bez
nich bola tá istá konfigurácia stratová. Keď som `minSlDistance` zapol na 0,2 % ceny, tesné stopy
zmizli úplne (120 → 0) a zisk tej konfigurácie spadol z 50 R na 2,9 R.

Teraz je `minSlDistance = 0,2 %` zapnuté natvrdo a navyše sa R každého obchodu pri výpočte
oreže na 10, aby jeden obchod nemohol určiť výsledok celého behu.

**Preto sú čísla v tabuľkách podstatne skromnejšie než v starších verziách.** Tie vysoké boli
z väčšej časti artefakt, nie edge.

## Čo v tabuľkách hľadať

- **na obchod** (expectancy v R) — koľko R prinesie priemerný obchod. Pozor: poradie v tabuľke
  sa neurčuje podľa tohto stĺpca, ale podľa jeho spodnej hranice spoľahlivosti.
- **PF** — hrubý zisk delený hrubou stratou; pod 1,2 to nestojí za nič.
- **max pokles** — najhorší prepad krivky v R. Pomer zisku k tomuto číslu je dôležitejší než
  samotný zisk.
- **winrate** pri ORB sedí okolo 35–50 % a sám o sebe nič nehovorí, lebo RRR je 1,5 až 3.
- Nastavenia s menej ako **150 obchodmi za rok** sa nezobrazujú vôbec — pri menšej vzorke je
  výsledok náhoda. Zmeral som to: pri 60–100 obchodoch vychádzali expectancy až 1,0 R, pri 400+
  obchodoch najviac 0,07 R.

## Poznámky k nastaveniam

- `maxTradesPerDay` je v skutočnosti **limit na seansu**, nie na deň. Pri zapnutých oboch
  seansách (`both`) je denný strop dvojnásobný.
- Typ vstupu `stop` sa nedá použiť — v stratégii je chyba a každý taký beh spadne. Testuje sa
  len `close` a `retest`. Podrobnosti v `CHYBA_V_STRATEGII.md`.
- Časť parametrov engine v danom režime vôbec nečíta: `rrRatio` platí len pri cieli `rr`,
  `tpAtrMult` len pri `atr`, `slAtrMult` len pri stope `atr`, `retestMaxBars` len pri vstupe
  `retest`. Dĺžka rangu pripúšťa len hodnoty 15, 30 a 60 minút.

## Súbory

- `prehlad/priebezne_vysledky.md` — tabuľky najlepších nastavení pre každý trh, obnovuje sa
  každých 15 minút, kým beh beží.
- `nastavenia/najlepsie.json` — presné parametre najlepšieho nastavenia pre každý trh.

Trhy: MNQ/USD (Databento), XAU/USD (Dukascopy), BTC/USDT:USDT (Binance futures).
Testované na poslednom roku, RRR 1,5 a vyššie, bez trailingu.
