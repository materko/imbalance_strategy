# MTK EMAS 1.0 BTC (C# jadro) — ako funguje

> V jednej vete: tá istá stratégia ako MTK EMAS 1.0 — kĺzavý priemer ukáže trend, vstupuje sa v jeho smere (štúdia: len longy nad EMA 200), stop a posúvaný stop sú v ATR —, len s nastaveniami pre BTC zo štúdie Mac mini.

Pravidlá, parametre aj kresby sú predlohy: [../../mtkemas/docs/VYSVETLIVKA.md](../../mtkemas/docs/VYSVETLIVKA.md).
C# jadro (NinjaTrader 8, MetaTrader 5) je zhodné s Python predlohou bar po bare (`tester/tests/test_csharp_parity_mtkemas.py`).

## Stop a cieľ
- Počiatočný stop = `slAtr` × ATR sviečky signálu, posúvaný stop `trailAtr` × ATR za najlepšou cenou, zámok na vstup
  pri `beAtR` R, cieľ `rrTarget` R; opačné kríženie obchod zavrie. Nastavenia: profily v `configs/` (najlepšie zo štúdie).

## Slovníček
- **ATR** — priemerná veľkosť sviečky; stop sa tak prispôsobí volatilite.
- **R** — vzdialenosť počiatočného stopu; zisk 2 R = dvojnásobok rizika.
- **Kontrakt** — BTCUSDT.P (Binance futures), CFD BTCUSD.
