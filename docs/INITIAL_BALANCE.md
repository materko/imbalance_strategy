# Initial Balance — štatistika ako IB Lab

[`tester/initial_balance.py`](../tester/initial_balance.py) počíta pre každý deň to isté, čo
[IB Lab](https://app.iblab.io/) (platená webová štatistika prvej hodiny seansy), a tými istými
pravidlami to agreguje do kariet a rozdelení. Logika je zreverzovaná z ich webu 20. 11. 2026
a overená deň po dni proti ich dátam (nižšie).

```
python -m tester.initial_balance --symbol ES                       # Statistics before break
python -m tester.initial_balance --symbol ES --scope post --dir bull --bias lowFirst
python -m tester.initial_balance --symbol MGC --dow 2 --period 3y --json
python -m tester.initial_balance --symbol ES --days-json es_ib.json  # riadky všetkých dní
```

Vo webapp je to karta **IB** (skupina Výskum) — tie isté filtre, karty a histogramy ako ich dashboard
plus tabuľka posledných dní ([WEBAPP.md](WEBAPP.md#karta-initial-balance)).

Dáta: 1m front-month CME futures z `data/archive/tester/databento/futures/` (ES, MGC, MYM, 6E od 2010,
MNQ od 2019) — rovnaký zdroj, aký majú oni (Databento `ohlcv-1m`, bez back-adjustmentu).

## Ako to počítajú

Server posiela predpočítané riadky dní (`GET /api/data/<nq|es|gc|si|cl|btc>/stats`, ~3,5 MB,
len s prihlásením) a prehliadač ich len filtruje a kreslí. Karta *Chart* počíta ten istý deň
v prehliadači zo sviečok (`/api/data/<inštr>/days/<dátum>`: 78 päťminútových sviečok
9:30–16:00 ET, 1m sviečky prierazového baru `c1b`, čas IB high/low po minútach) — z toho kódu
je prepis. Časy majú v UTC, sloty v ET.

| pole | definícia |
|---|---|
| IB | high/low 1m sviečok 9:30–10:29 ET (Londýn 3:00–3:59); seansa do 16:00 (Londýn 8:30) |
| bias | `lowFirst` (býčí), keď IB low vzniklo skôr ako IB high, inak `highFirst` |
| prieraz (`slot`) | prvá 5m sviečka po IB, ktorej knôt je **ostro** nad IB high / pod IB low; keď jedna sviečka prerazí oba okraje, berie sa ako medvedí |
| double break | počas seansy prerazené oba okraje; `dblSlot` = sviečka druhého |
| max retracement | od minúty po prieraze (v 1m sviečkach prierazového baru) do konca seansy najhlbší návrat do IB: 0 = prerazený okraj, 1 = opačný |
| max extension | od prierazovej sviečky vrátane najďalej za prerazený okraj |
| HOS/LOS („magic") | býčí deň: najnižšie low *pred* maximom seansy, od minúty po prieraze; môže byť záporné (zóny P) |
| before-break | od konca IB po prierazovú sviečku **vrátane** najhlbší pohyb proti prierazu, meraný od okraja biasu (IB high pri `lowFirst`) |
| IB close | close poslednej 5m sviečky IB, od okraja biasu (0 až 1) |
| IB % | (high − low) / stred × 100 |
| zóny | po 0,1; retracement zaokrúhli na stotiny pred delením, extension nie |
| časy | do 5m slotu (aj keď sa našli v 1m sviečkach) |

Agregácia: high/low/none zo všetkých dní, *single break* zo všetkých dní s prierazom, všetko
ostatné len z dní, kde max retracement existuje (prieraz v poslednej sviečke vypadne). Biela
čiara = 70. percentil (lineárna interpolácia), zlatá = medián; časová karta ukazuje koniec 5m
slotu s mediánom. Histogramy vynechajú hodnoty ≥ 3,0 IB (outliery). Pri zvolenom biase sa
before-break a čas prierazu počítajú len z dní s prvým prierazom v smere biasu (*Break with
bias: True*) alebo proti nemu (*False*, vtedy 30. percentil).

## Overenie (20. 11. 2026)

* **ES 2010-06-07 – 2026-10-19, deň po dni** (4 205 spoločných dní): všetky polia zhodné okrem
  5 dní, kde sa líšia dáta — 2018-03-09, 2018-06-08, 2020-03-13, 2020-06-12 rolujú na nový
  kontrakt o deň skôr ako náš importér; 2020-02-28 majú len 18 sviečok; 2020-06-30 im chýba.
* **Karty** — `summary()` nad ich vlastnými riadkami ES dáva presne ich čísla (before break
  52,7 / 44,9 / 2,4 %, 10:50, −0,31 · 10:35; after break bull 2 214 dní, 73,7 / 78,0 / 68,7 /
  49,6 / 15,4 %, retr 0,50 · 13:20, ext 0,59 · 14:05, HOS/LOS 0,17 · 11:20).
* **NQ (ich) proti MNQ (náš)** od 2019-05: smer, bias a prieraz zhodné na 99,6 % dní, zóny na
  ~95 % — mikro a plný kontrakt sa líšia o tiky. Pre zhodu s ich NQ treba NQ dáta.

## Čo chýba

* **News filter** berie FOMC / CPI / NFP z [`tester/calendar.py`](../tester/calendar.py), ktorý
  pokrýva len 2021–2026; dni mimo pokrytia do filtra nejdú. IB Lab má zoznamy od 2010 a
  „bank holiday" vrátane Columbus/Veterans Day.
* NQ, GC, SI, CL, BTC futures v archíve nie sú (máme MNQ, MGC, MYM, 6E, ES).
