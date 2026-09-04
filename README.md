# imbalance_strategy

## Súbory

| Súbor | Popis |
|---|---|
| [`imbalance_strategy_FULL.pine`](imbalance_strategy_FULL.pine) | **REFERENČNÁ VERZIA** — Pine v5, 2539 riadkov, 115 inputov, SK. Plná funkcionalita: SD zóny + IMB / Pin Bar / Engulfing entry, S/R, Likvidita (sweep), Market Structure (BOS/CHoCH), Elliott Waves, dashboard. (PickMyTrade sa do Pythonu neportuje.) **Zodpovedá screenshotom nastavení.** |
| [`imbalance_strategy_SD_IMB.pine`](imbalance_strategy_SD_IMB.pine) | Stripped build — Pine v6, 1569 riadkov, 80 inputov, EN. Len SD zóny + IMB entry model. Bez novej logiky oproti FULL (iba preklad + `margin_long/short=0`). |
| [`Imbalance_strategy.pine`](Imbalance_strategy.pine) | Najstaršia verzia — Pine v5, „Imbalance strategy", 57 inputov. |
| [`docs/tv_settings_2026-09-03.md`](docs/tv_settings_2026-09-03.md) | Kompletné TradingView nastavenia + rozdiely oproti defaultom v kóde |
| [`docs/chart_reference_BTCUSD_3m.md`](docs/chart_reference_BTCUSD_3m.md) | Čo stratégia kreslí na graf + konkrétne scény na verifikáciu portu |
| [`docs/cely_kod_original.rtf`](docs/cely_kod_original.rtf) | Originál (RTF), z ktorého bol extrahovaný `imbalance_strategy_FULL.pine` |

**Plán:** prepísať do Pythonu / Freqtrade so zachovaním rovnakých nastavení a rovnakého vykreslovania na grafoch.
Referenčný setup: BTCUSD 3m (Coinbase), Long only, RR 1:1 — 17 obchodov, 8W/9L, 47 % winrate.

## Python port

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

| Cesta | Popis |
|---|---|
| [`ibs/core/types.py`](ibs/core/types.py) | `Bar`, `HTFWindow`, `InstrumentSpec`, `SizeSpec`, enumy |
| [`ibs/core/config.py`](ibs/core/config.py) | `IBSConfig` — všetkých 115 Pine vstupov + validácia + profily |
| [`ibs/configs/`](ibs/configs) | JSON profily (len odchýlky od Pine defaultov): `mnq_3m`, `btcusd_3m_coinbase`, `btcusdt_3m_binance` |
| [`ibs/tests/test_pine_parity.py`](ibs/tests/test_pine_parity.py) | parsuje `imbalance_strategy_FULL.pine` a stráži, že config nespadol z Pine originálu |

Návrh architektúry a rozhodnutia: [`docs/ARCHITECTURE_port.md`](docs/ARCHITECTURE_port.md)
