# IVB 1.0 — Initial Volatility Breakout — ako funguje

_Variant na MGC: logika a parametre sú tie isté ako v `ivb` (MNQ); prahy v ATR sa prispôsobia trhu sami, prahy v bodoch treba nastaviť v profile._

> V jednej vete: keď je prvá polhodina New Yorku úzka oproti posledným dňom, čaká sa, kedy ju cena prerazí so zvýšeným objemom, a ide sa v smere prierazu.

Prepis cudzej stratégie (Rust, platforma `rq_sdk`), ktorú používateľ poslal 29. 10. 2026 **len na porovnanie** — pravidlá aj predvolené čísla sú presne z predlohy.

## Initial Balance (IB)
- **IB** je rozsah (high a low) prvých 30 minút seansy New York: **9:30–10:00 NY** (15:30–16:00 u nás).
- Stratégia si pamätá šírku IB z posledných **10 dní**.

## Kedy vstúpi
Od 10:00 do 16:00 NY, keď nie je v pozícii a ešte nevyčerpala 2 pokusy za deň, a naraz platí:
- **stlačený deň** — dnešný IB je najviac **0,9 ×** priemer posledných IB,
- **nárast objemu** — objem sviečky je aspoň **1,1 ×** priemer posledných 5 sviečok seansy,
- **prieraz** — sviečka **zavrie nad high IB** → long, **pod low IB** → short; vstup trhom.

## Stop a cieľ
- **Stop 3 × ATR**, **cieľ 2 × ATR** od zavretia sviečky prierazu. Cieľ je bližšie ako stop, takže stratégia potrebuje úspešnosť nad ~60 %.
- Pozícia sa predvolene **nezatvára na konci dňa** (dá sa zapnúť).

## Zvláštnosti predlohy (ponechané kvôli porovnaniu)
- Pokus za deň sa započíta, keď platí stlačený IB a objem, **aj keď prieraz nenastal** — dva také bary vyčerpajú deň bez obchodu.
- Šírka IB sa zapisuje na sviečkach 10:00–10:04 — na 1m grafe **päťkrát za deň**, čo skresľuje priemer. Na 5m grafe raz.
- Veľkosť pozície predloha počíta z 2 % účtu; tu z rizika v $ (`riskDollar`).

## Slovníček
- **ATR** — priemerný rozsah sviečky (Wilder, 14 sviečok grafu); stop a cieľ sa ním prispôsobia volatilite.
- **Objem RTH** — objem sviečok v riadnej seanse 9:30–16:00 NY.
- **Prieraz zavretím** — rozhoduje cena zavretia sviečky, nie knôt.
