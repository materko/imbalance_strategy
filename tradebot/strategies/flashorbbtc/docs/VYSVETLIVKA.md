# FLASH TRIGGER ORB 1.0 (BTC) — ako funguje

_Variant na BTCUSDT.P (Binance futures): logika a parametre sú tie isté ako v `flashorb` (MNQ). Nastavenia z MNQ sa na BTC neprenášajú — vlastné hľadá ladenie a smernica (poplatok maker 0,02 %)._

> V jednej vete: high a low jednej vybranej sviečky (predvolene 14:30 UTC) vytvorí rozpätie a prvé zavretie za ním otvorí obchod.

Prepis Rust stratégie „The Flash Trigger ORB“ (roboquant.dev), ktorú poslal používateľ 29. 10. 2026.

## Rozpätie
- Sviečka s časom **14:30 UTC** (= 9:30 NY v zime, 10:30 NY v lete — predloha posun nerieši) dá high a low.
- Voliteľne len vybrané dni v týždni.

## Kedy vstúpi
- Od ďalšej sviečky: **zavretie nad high** → long, **pod low** → short. Jeden obchod za deň.

## Stop a cieľ
- **Stop** na druhej strane sviečky, **cieľ 3 ×** vzdialenosť stopu (RR 3).
- Voliteľný trailing v bodoch; pozícia sa zatvára o 23:59 UTC (pri testoch podľa smernice vypnuté).

## Slovníček
- **ORB** — prieraz otváracieho rozpätia.
- **RR** — pomer cieľa k stopu.
