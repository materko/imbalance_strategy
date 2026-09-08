# Parita celkového zisku s TradingView — 2026-09-08

Doteraz golden test strážil **obchody** (čas, vstupnú a výstupnú cenu, veľkosť, winrate),
nie **výsledok**. Otázka bola, či pri rovnakom kapitáli sedí aj celkový zisk v mene aj
v percentách — a to v oboch smeroch: v simulátore aj v Testeri cez Freqtrade.

Referencia je `tester/tests/golden/tv_btcusdt_binance_3m.json`: BINANCE:BTCUSDT.P 3m,
Aug 24 – Sep 4 2026, profil `golden_binance_btcusdt_3m` (1 BTC na obchod,
`legacyPineSizing`, bez poplatkov), **initial capital 10 000**.

| | TradingView | simulátor | Freqtrade |
|---|---|---|---|
| obchodov | 5 (3W/2L) | 5 (3W/2L) | 5 (3W/2L) |
| celkový PnL | −86,0 USD | −86,1 USD | −86,0 USD |
| PnL v % | −0,86 % | −0,861 % | −0,86 % |
| profit factor | 0,84 | 0,84 | 0,84 |
| max drawdown | 5,67 % | — | 5,28 % |

Sedí to. Zvyšné rozdiely sú dva a oba sú vysvetlené nižšie.

## Percento sedí len s rovnakým kapitálom

TradingView počíta „Net Profit %" z **initial capital**. Sto USD zisku je 1 % na účte
10 000 a 0,025 % na účte 400 000 — to isté číslo, iné percento. Aby percento sedelo,
musí Tester dostať ten istý kapitál:

```bash
PY -m tester.webapp.cli run --profile golden_binance_btcusdt_3m \
   --timerange 20260824-20260904 --fee 0 --wallet 10000 --set leverage=20 \
   --note "parita s TradingView"
```

Doterajší odporúčaný postup v CLAUDE.md (`--fee 0 --wallet 400000`) dá **správny PnL v mene**,
ale percento z inej základne. Na porovnanie s grafom treba peňaženku rovnú kapitálu grafu.

## Páka: TradingView margin nerieši, Freqtrade áno

Strategy Tester nechá kúpiť 2 BTC (157 530 USD) na účte za 10 000 a nič nenamieta.
Freqtrade pozíciu oreže na to, čo sa zmestí do peňaženky:

| páka | qty 4. obchodu | PnL | v % |
|---|---|---|---|
| 10 | 1,212 namiesto 2 | −110,45 USD | −1,10 % |
| 20 | 2,0 | −86,0 USD | −0,86 % |

Pri páke 10 potrebuje 2 BTC maržu 15 753 > 10 000, takže Freqtrade dal menej — a výsledok
sa rozišiel o 24 USD, hoci ceny všetkých piatich obchodov sedeli na cent. Páka 20 stačí,
vyššia už nič nemení. Adaptér to hlási len vtedy, keď je orezanie väčšie než promile
(`stake orezany z … na …`), takže pri drobných orezaniach treba pozerať na qty.

**Nie je to argument za páku 20 v reálnom obchodovaní** — je to len spôsob, ako v Testeri
vypnúť margin obmedzenie, ktoré TradingView nemá.

## Chyba, ktorá sa pritom našla: pozícia o krok menšia

Aj po zrovnaní kapitálu vychádzalo −85,74 namiesto −86,0 a veľkosti boli 0,999 / 1,999
namiesto 1 a 2. Príčina je v spätnom prepočte vo Freqtrade
(`optimize/backtesting.py::_enter_trade`):

```python
amount_p = (stake_amount / propose_rate) * leverage
amount = amount_to_contract_precision(amount_p, precision_amount, ...)   # OREŽE, nezaokrúhli
```

Adaptér dáva stake ako `qty * cena / páka`. Delenie a násobenie tou istou cenou ale
v plávajúcej rádovej čiarke presné nie je:

```python
>>> (1.0 * 79419.5 / 20) / 79419.5 * 20
0.9999999999999999          # a po orezaní na krok 0,001 z toho je 0.999
```

Trafí to len niektoré ceny (79 419,5 a 79 022,0 áno, 80 516,1 a 79 250,0 nie), takže sa
to prejavovalo ako nevysvetliteľný rozdiel pár desatín na behu. Oprava je rezerva
zlomku promile v `custom_stake_amount` (`_STAKE_EPS = 1e-12`) — krok kontraktu je o desať
rádov väčší, takže na veľkosť pozície nemá vplyv, len prekryje chybu zaokrúhlenia.
Stráži to `tradebot/tests/test_freqtrade_entries.py::test_stake_prezije_orezanie_na_krok_kontraktu`
na reálnych cenách z tohto behu.

Dopad na staršie behy: veľkosť pozície bola miestami o jeden krok kontraktu menšia, než
plán žiadal — na BTC pri kroku 0,001 rádovo 0,1 % pozície, teda šum, ale systematicky
v neprospech. Merania sa tým neprepisujú, čísla sa posunú o promile.

## Čo sa neporovnáva

**Max drawdown** (5,67 % v TradingView, 5,28 % vo Freqtrade) sa počíta inak: TradingView
berie priebeh equity vrátane otvorenej pozície, Freqtrade svoju equity krivku. Toto meranie
ho nerieši; na úvahy o veľkosti účtu je `python -m tester.montecarlo`.

## Čo z toho platí ďalej

* Golden test odteraz stráži aj súčet, nielen jednotlivé obchody:
  `tester/tests/test_golden_tv_binance.py::test_celkovy_zisk_a_percento_sedia_s_tradingview`.
* Na porovnanie s grafom v TradingView: `--wallet <initial capital z grafu> --fee 0`
  a páka taká, aby sa najväčšia pozícia zmestila.
* Percento sa dá porovnávať len pri rovnakom kapitáli; break-even poplatok od kapitálu
  nezávisí a preto ostáva hlavnou metrikou na porovnávanie behov medzi sebou.
