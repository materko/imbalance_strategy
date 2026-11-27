# Zavedenie SMERNICE V2 — podklady pre vývojára (27. 11. 2026)

- **[ZADANIE_IT.md](ZADANIE_IT.md)** — čo naprogramovať: úlohy U1–U11 s presnými číslami, vzorcami, súbormi a akceptáciou.
- **[SMERNICA_V2.md](SMERNICA_V2.md)** — schválená smernica (rovnaká ako `docs/SMERNICA_TESTOVANIA.md`). Pri rozpore platí smernica.
- `01–23_*.md` — debata agentov A (Prokurátor), B (Inžinier) a kontrola C, z ktorej smernica vznikla; `VYCUC.md` (výcuc),
  `SUMAR.md` (zhrnutie), `KONVERZACIA.md` (všetko spolu).
- Merania a skripty: `data_kvalita.json`, `data_noc_roly.json`, `dq_scan.py`, `dq_night_rolls.py` (kvalita dát a rolovanie),
  `obchody_sila.py` (štatistická sila trezoru), `cfd_fill*.py`, `cfd_tp_touch.py`, `cfd_fill_out.txt` (CFD fill model zo živých fillov).
- **`nightsearch_kod/`** — snímka kódu automatu z `.nightsearch/` na Mac mini (v gite inak nie je): `glsearch.py`, `glhyper.py`,
  `glwr.py`, `glrr.py`, `gldash.py`, `glwebvyber.py`, `glmorning.sh`… Zadanie sa naň odvoláva ako `.nightsearch/<súbor>`.
  Bez stavových súborov, logov a tokenov. Úpravy robte v `.nightsearch/` na Mac mini (alebo sa dohodnite na presune do repa).
- **`zaklad_profily/`** — skript, ktorý vyrobil `tradebot/strategies/*/configs/ZAKLAD_<trh>.json` (predvolené hodnoty kódu,
  obdobie L, prahy v bodoch prepočítané pomerom mediánu denného ATR(14) v pevnej cene trhu), a tabuľka ATR a cien.

Stav k 27. 11. 2026: vyladené profily, analytika a história behov sú v archíve; staré profily sú len vstupy testov parity
v `tester/tests/fixtures/profiles/` (`TEST_PROFILES_DIR`). Automat hľadania a ranné nahrávanie sú zastavené, kým nie je V2 v kóde.
Otvorené po kontrole A (`23_A_zaklad.md`): domovský trh predvolených hodnôt je pri všetkých stratégiách predpoklad MNQ
(treba ručný zoznam s dôkazom) a 23 profilov `ZAKLAD_6E` je neplatných bez zmeny kódu (polia ako `slPoints` mimo rozsahu Pine).
Pred pushom: `pytest` (14 testov padá už pred zmenami V2 — kalendár SPRÁV, NT nástroje, live žurnál, šablóny MT5,
vstupný model 4 stratégií, host pull), `ruff check .`, ESLint webapp, `python -m tradebot.adapters.csharp.build --force`.
