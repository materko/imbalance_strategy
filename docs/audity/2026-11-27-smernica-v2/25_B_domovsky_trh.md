# 25 · Inžinier B · Domovský trh predvolených hodnôt (27. 11. 2026)

Zdroj: `25_B_domovsky_trh.json` (154 kľúčov z registra). Bodové pole = `*Points`, `*Pts`, `*Ticks` alebo
SIZE_FIELDS s jednotkou abs/ticks a s predvolenou hodnotou v tej jednotke. Všetky kópie (…es, …mgc, …mym, …eur,
…btc, …net, …eod) majú bodové defaulty **zhodné s predlohou** (overené strojovo), takže trh dedia.

## Súhrn

| domovský trh | počet | z toho |
|---|---|---|
| `mnq_databento` | 52 | IBS rodina (13), TKS rodina (13), MTK ZONE (3), ORB 15 + MTK ORB (5), Flash ORB (4), VOLT BREAK (2), NY VA ES (2), vwapdrift, svp, fvgpolarity (2), fpc, mag7, dailyopen (2), nb, sweepfvg |
| `es_databento` | 4 | m2, m2mnq, m2eur, m2mgc |
| `6e_databento` | 4 | scalp3ma, scalp3mamgc, asiasweep, asiasweepeur |
| `mgc_databento`, `mym_databento`, `btcusdt_binance` | 0 | — |
| `bez_bodov` | 94 | 89 bez bodového poľa a 5 s jediným bodovým poľom na 0 = vypnuté (jss, crt, fibo, fibomgc, fibomgcnet) |

(52 + 4 + 4 + 94 = 154. V MNQ sú započítané aj voltbreak a voltbreaknet, ktoré podľa formálnej definície nemajú
žiadne bodové pole. Prahy majú ukryté v dolároch NQ, pozri nižšie.)

## Kde domovský trh nie je MNQ
- **ES:** `m2`, `m2mnq`, `m2eur`, `m2mgc`. Predloha je ES 1m (m2/config.py:12, commit 61d88a5dd: „`m2` (S&P 500)“).
  Jediné pole je `slTicks=1`, takže prepočet ATR z MNQ by ho skreslil len málo. Napriek tomu je pre `m2mnq`
  chybný predpoklad, že MNQ je domov.
- **6E:** `scalp3ma` a `scalp3mamgc`. `slPoints=0.0005` = 5 pipov EURUSD (scalp3ma/config.py:13 a :130).
  Pole je predvolene neaktívne (`slMode=ATR`). Žiadny ZAKLAD_<trh> ho neprepisuje, takže všade platí 0,0005,
  aj na MNQ (0,0005 bodu, pri `slMode=points` by to bol nezmysel). Webapp ich pritom zaraďuje pod NASDAQ a ZLATO.
- **6E:** `asiasweep` a `asiasweepeur`. `vpRowTicks=10` je podľa komentára „EURUSD: 10 tickov = 1 pip“
  (asiasweep/config.py:157). Istota je stredná, lebo je to len komentár k jednému tickovému poľu. ZAKLAD prepočet
  šiel opačným smerom: ZAKLAD_MNQ má 10 a ZAKLAD_6E má 2, hoci domov je 6E a správne by bolo 10.

## Istota nízka (MNQ len odvodené)
- `orb15`, `orb15es`, `orb15mgc`, `mtkorb`, `mtkorbnet`: `targetPoints=40` pochádza z roboquant šablóny, ktorá trh
  neuvádza. Predvolene je pole neaktívne (`targetMode=0`). Pozor: `mtkorb` je stratégia na zlato a nesie 40 bodov.
- `flashorb`, `flashorbes`, `flashorbmgc`, `flashorbbtc`: `trailActivatePoints=50` a `trailBufferPoints=20`
  pochádzajú z roboquant šablóny bez uvedeného trhu. Trailing je predvolene vypnutý.
- `sweepfvg`: `tpPoints=50` bez zmienky trhu („Parametre neladené“). Predvolene je neaktívne (`tpMode=RR`).

Strednú istotu majú len `nb` (jeden tick, zaradenie NASDAQ), `asiasweep` a `asiasweepeur`.

## Nálezy mimo definície (pre audit polí, riziko z 22_B)
- **voltbreak a voltbreaknet majú skryté bodové prahy** `tpUsd=800`, `slUsd=1500` a `usdPerPoint=20`, čo je 40 a 75
  bodov NQ (voltbreak/config.py:84). Nespĺňajú vzor `*Points` a nie sú ani v SIZE_FIELDS, takže ich prepočet
  ZAKLAD nevidí.
- `mag7.slOpenBuf=2` sú body MNQ mimo vzoru. Pole je aktívne pri predvolenom `slMode=OPEN`.
- Kópie na iných trhoch nesú defaulty MNQ, napr. `ibsentryeur`, `mtkzoneeur`, `tkseur`, `dailyopenbtc`,
  `tksbtc`, `flashorbbtc`, `orb15mgc` a `fvgpolaritymgc`. Prepočet je pri nich nutný a domov MNQ je správny.
- Všetky ostatné domovy MNQ majú priamy dôkaz v `config.py` (NQ/MNQ v komentári) alebo v Pine (iCloud
  VOLUME-PROFILE pre mtkzone a nyva).
