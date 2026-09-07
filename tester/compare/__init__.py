"""Porovnávacie behy: Pine ↔ port, MultiCharts ↔ emulátor ↔ Freqtrade.

`scan_zones` a `scan_trades` prehrajú engine offline nad burzovými dátami alebo nad
surovým Dukascopy CSV, `mc_log_trades` vytiahne obchody z logu MultiCharts študie
a `mc_compare` oba zoznamy spáruje podľa vstupnej ceny.
"""
