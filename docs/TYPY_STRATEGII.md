# Aký typ stratégie to je — a prečo je to dôležité

Od charakteru stratégie závisí, **čo je normálne a čo je problém**. Winrate 28 % je pri
prerazení v poriadku a pri protitrendovej stratégii katastrofa. Kto ladí protitrendovú
stratégiu na maximálny payoff, pracuje proti jej podstate; kto sa pri prerazení vystraší
zo šiestich strát v rade, vypne niečo, čo funguje.

Preto sa typ **meria**, nie odhaduje z názvu — karta **Analytika** vo webapp to spočíta
z obchodov spolu s tým, ktorá skupina obchodov kazí výsledok
([docs/HYPEROPT.md](HYPEROPT.md) je o tom, čo s tým potom).

## Čo sa meria

| číslo | čo hovorí |
|---|---|
| **pohyb pred vstupom** (v ATR) | kladný = vstup po pohybe v smere obchodu, záporný = proti nemu |
| **winrate** | podiel ziskových |
| **payoff** | priemerný zisk delený priemernou stratou |
| **medián držania** (v baroch grafu) | scalp / intradenná / swingová |
| **obchodov za deň** | frekvencia |
| **šikmosť výnosov** | kladná = málo veľkých ziskov, záporná = veľa malých a občas rana |
| **teplo pred ziskom** (MAE/MFE) | koľko obchod znesie proti sebe, než sa otočí |
| **zmes výstupov** | koľko končí na TP, na stope, na čase |

Rozhodujúci je **pohyb pred vstupom**. Winrate aj payoff sa dajú nastaviť aj proti
charakteru stratégie — stačí posunúť TP a z prerazenia je opticky „vysoký winrate".
To, či stratégia vstupuje *po* pohybe alebo *proti* nemu, sa takto oklamať nedá.

Počíta sa ako zmena ceny za posledných päť barov pred vstupom, so znamienkom podľa smeru
obchodu, delená priemerným rozsahom baru v tom okne. Delenie rozsahom je to, čo umožňuje
porovnať BTC s EURUSD.

## Typy

### Prerazenie (breakout)
**Pozná sa:** vstup po pohybe v smere obchodu, nízky winrate, vysoký payoff, krátke držanie.

Vstupuje sa do pohybu, ktorý už začal, s tým, že bude pokračovať. Väčšina prerazení
nevydrží — platí sa nimi za tie, ktoré vydržia.

- **Normálne:** dlhé série strát. Winrate pod 40 % je v poriadku.
- **Pozor:** falošné prerazenia v úzkom rozsahu. Filter na veľkosť pohybu a na to, či trh
  vôbec nie je v rozsahu, býva silnejšia páka než čokoľvek na výstupe.
- **Ladiť:** prahy vstupu a RR. **Nie winrate** — ten sa dá zvýšiť len skrátením TP, čím
  sa stratégia pokazí.

### Trendová (momentum)
**Pozná sa:** vstup v smere pohybu, dlhé držanie, nízky winrate, veľmi vysoký payoff.

Rozdiel oproti prerazeniu je v držaní: prerazenie berie prvý kus pohybu, trendová sa ho
snaží odsedieť celý. Výsledok nesie málo obchodov.

- **Normálne:** mesiace bez zisku a potom jeden obchod, ktorý vyrovná rok. Rovná krivka
  kapitálu sa od tohto typu čakať nedá.
- **Pozor:** vyhodnotenie na krátkom okne. Keď výsledok nesie päť obchodov z dvesto, jedno
  okno nehovorí nič a Monte Carlo interval bude široký.
- **Ladiť:** trailing a dĺžku držania. Skrátenie TP tento typ zabije.

### Protitrendová (mean reversion)
**Pozná sa:** vstup proti poslednému pohybu, vysoký winrate, nízky payoff, krátke držanie.

Stavia na tom, že prehnaný pohyb sa vráti. Zarába frekvenciou, nie veľkosťou.

- **Normálne:** winrate nad 60 % a payoff pod 1.
- **Pozor:** jedna strata môže zmazať mesiac. Stop je tu dôležitejší než vstup;
  `maxLossDollar` a limit na drawdown majú väčší význam než pri ostatných typoch. A v
  silnom trende tento typ dostáva rany — filter režimu je namieste.
- **Ladiť:** stop a filter režimu. Zvyšovanie RR väčšinou len zníži winrate a nič nepridá.

### Scalping
**Pozná sa:** veľa obchodov, veľmi krátke držanie, payoff okolo 1, winrate okolo 50 %.

- **Normálne:** edge na obchod je rádovo taký veľký ako poplatok.
- **Pozor:** poplatky a slippage rozhodujú o všetkom. Beh s `--fee 0` je pri tomto type
  bezcenný.
- **Ladiť:** break-even poplatok, nie PnL. A počet obchodov — menej lepších je viac.

### Formácia / štruktúra
**Pozná sa:** vstup na konkrétnej konfigurácii; predchádzajúci pohyb nie je systematicky
ani v smere, ani proti.

- **Normálne:** zmes. Časť obchodov sa chová ako prerazenie, časť ako návrat.
- **Pozor:** priemer skrýva dve rôzne populácie. Práve pri tomto type sa najviac oplatí
  rozdeliť obchody na skupiny.
- **Ladiť:** podmienky vstupu (ktoré modely zapnuté) a až potom výstup.

### Swingová
**Pozná sa:** málo obchodov, držanie v dňoch, payoff nad 1.

- **Normálne:** desiatky obchodov za rok, teda nutne slabá štatistika.
- **Pozor:** málo obchodov = ľahké pretrénovanie. Hyperopt tu prefituje najrýchlejšie.
- **Ladiť:** skôr výber trhu a obdobia než jednotlivé prahy.

## Prečo pravidlá a nie model

Zaradenie sú pravidlá nad zmeranými číslami. Nie preto, že by klasifikátor nešiel, ale
preto, že tu treba vidieť **prečo**: „vstup po pohybe +1,01 ATR, winrate 29,7 %, payoff
2,30, medián držania 53 barov" je vysvetlenie, s ktorým sa dá pracovať, kým „92 %
breakout" nie je. Pri desiatkach behov by sa model aj tak nemal na čom učiť.

Preto výstup vždy obsahuje dôkazy aj **istotu** (`dobrá` / `priemerná` / `slabá`). Slabá
istota znamená buď málo obchodov (pod 20), alebo že sa nedal zmerať pohyb pred vstupom —
napríklad keď sa zliali obchody z viacerých párov, lebo sviečky sú párové.

## Ako sa to zmeria na inej stratégii

Nijako zvlášť — merajú sa veci, ktoré má každá stratégia rovnaké (`trades.json` píše
Freqtrade) plus sviečky páru. Nová stratégia teda nemusí napísať nič a `tester.character`
ju zaradí rovnako. Dve vlastnosti sú voliteľné a stoja na tom, čo o sebe stratégia povie
v registry:

| chcem | treba na SPEC |
|---|---|
| vzdialenosť stopu a plánovaný RR obchodu | `sl_kind`, `tp_kind` — mená kresieb, ktoré nesú SL a TP box |
| odkaz „preladiť tento parameter" z analytiky | `hyperopt_cls.FEATURE_PARAMS` — `vlastnosť → pole configu` |

Z CLI:

```bash
PY -m tester.webapp.cli show <run_id>          # jeden beh
```

a v prehliadači karta **Analytika**, kde sa dá vybrať viac behov naraz (jeden beh má na
delenie na skupiny málo obchodov).

## Čo z toho vyšlo na IBS

Zmerané na 969 obchodoch z desiatich behov `BTC/USDT:USDT` 3m:

```
Prerazenie (breakout)   (istota dobrá)
  - vstup po pohybe v smere obchodu (+1,01 ATR za 5 barov)
  - medián držania 53,5 barov grafu
  - winrate 29,72 %, payoff 2,295
  - 0,48 obchodov za deň
  - šikmosť výnosov +7,59
  výstupy: stop_loss 42 %, session_end 24 %, trailing_stop_loss 21 %, roi 13 %
```

Je to učebnicové prerazenie: vstup po pohybe, tri zo štyroch obchodov končia stratou,
zarábajú tie, ktoré vydržia. Z toho vyplýva aj to, čo pri ňom **nemá zmysel** ladiť —
winrate. A vyplýva z toho, že 42 % výstupov na stope nie je chyba, ale cena za tento typ.

Čo z tých čísel vyčnieva a stojí za pozretie: **24 % obchodov končí na čase**
(`session_end`), nie na pláne. To nie je vlastnosť prerazenia, to je nastavenie okna
seansy — a analytika na to ukazuje `closeAtSessionEnd`.
