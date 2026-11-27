# 29 C — kontrola: ZAKLAD len pre trh kópie (27. 11. 2026, 19:00)

Kontrolór C. Nič som neupravoval, len čítal a spúšťal (build.py bez --apply; porovnanie so suchým behom
cez podvrhnutý `Path.write_text`, nič sa nezapísalo).

## Verdikt: **commitnúť NIE v tejto podobe** — po oprave N1 (a vyriešení N2/N3) áno.

Jadro opravy je správne: 83 kópií × 5 zmazaných = 415, zostáva 509, build.py vyrobí presne tých 509
s rovnakým obsahom bajt po bajte, webapp ich ukazuje správne. Chyby sú okolo nej.

## Čo sedí (dôkaz)

- `build.py` bez --apply: `stratégií 154 profilov 509`. Suchý beh s --apply a podvrhnutým zápisom:
  generované 509, na disku 509, iba v jednom 0 / 0, rozdiel v obsahu 0.
- `git status`: 415 zmazaní = 83 stratégií × presne 5 súborov, žiadny iný ZAKLAD zmazaný.
- Každá z 83 kópií (podľa `copy_market`) má na disku práve jeden `ZAKLAD_<svoj trh>` a jej `default_profile`
  v `__init__.py` naň ukazuje (všetkých 83 skontrolovaných). Všetkých 509 ZAKLAD má `_strategy`, `_instrument`
  a `_timerange` zhodné s `MK` svojho trhu.
- Pravidlo podľa prípony nemá false positive: `ibszones`, `trendlines` sú vylúčené; `nyvaes`, `sdeur`, `sdeurnet`
  (bez predlohy v registri), `m2mnq`, `nqpreces`, `nqprecmgc`, `scalp3mamgc`, `nocponmym` sú zachytené správne.
- Webapp (PID 48364, beží od 8:29) netreba reštartovať: `/api/strategies/<k>/meta` pre všetkých 154 kľúčov —
  0 kópií s iným zoznamom ZAKLAD (napr. `tksmgc` → `['ZAKLAD_MGC']`). Pozn.: `/api/meta?strategy=…` parameter
  ignoruje a vracia profily `ibs`; správny endpoint je `/api/strategies/<k>/meta`.

## Nálezy

**N1 (blokuje) — `tester/webapp_vyber.json`, sekcia `"dole"` (riadok 258 a ďalej) nebola opravená.**
Opravená je len sekcia `"strategies"` (15 kópií). V `"dole"` má 68 kópií stále všetkých 6 ZAKLAD →
340 odkazov na zmazané súbory (napr. `tksmgc`, `noaes`, `wprmym`, `sdeur`, `spravyeur`, `nyvaes`, `tkseur` …).
Tvrdenie „kópie majú len [ZAKLAD_<svoj trh>]“ je teda nepravdivé pre 68 z 83. Funkčne to dnes neškodí
(`tester/webapp/vyber.py:68–73` `filter_names` robí prienik s existujúcimi súbormi), ale súbor je nekonzistentný
s diskom — a keby niekto profily znova vyrobil po starom, vrátia sa do webapp bez varovania.

**N2 (pravidlo minulo kópie) — `mtkorb`, `mtkorbnet` sú stratégie len pre MGC, ale majú 6 ZAKLAD.**
- `tradebot/strategies/mtkorb/__init__.py:1` „prieraz opening range … na zlate“, `:18` `title="MTK ORB (MGC)"`,
  `:21` `default_profile="ZAKLAD_MGC"`; `tradebot/strategies/mtkorbnet/__init__.py:26` `"MTK ORB MGC (C# jadro)"`.
- `settings.js:558` `mtkorb: ["ZLATO", …]`. Kľúč nemá príponu trhu, preto ho `copy_market` nevidí.
- Dôsledok: 10 zbytočných profilov, z toho 2 neplatné (`mtkorb 6E`, `mtkorbnet 6E` — targetPoints mimo rozsahu Pine).
  Riešenie: výslovný zoznam `_COPY_EXTRA = {"mtkorb": "MGC", "mtkorbnet": "MGC"}` v build.py. Potom 499 profilov
  a 8 neplatných.
- Navyše `domov.json` (`mtkorb`/`mtkorbnet`) má `home = mnq_databento`, istota nízka — jediný ZAKLAD (MGC)
  je tak prepočítaný z bodov MNQ cez pomer ATR. Pre stratégiu „ladenú na MGC 2010–2024“ je to sporné.

**N3 (na rozhodnutie používateľa) — `spravy`, `spravynet` sú podľa kódu len pre zlato.**
`tradebot/strategies/spravy/__init__.py:1` „SPRÁVY 3.0 — zlato (MGC) po červených správach USA“,
`spravy/config.py:1–3` výskum len na MGC, `settings.js:565` `spravy: ["ZLATO", …]`; pre 6E existuje samostatná
kópia `spravyeur`. Napriek tomu `spravy`/`spravynet` majú ZAKLAD aj pre MNQ, ES, MYM, BTC, 6E. Nie je to kópia
podľa názvu (je to predloha), ale logicky je to stratégia jedného trhu. Rovnako `nqprec` („NQ PRECISION“),
`nocpon` („nočný drift Nasdaqu“), `noa` („momentum na Nasdaqu“) a `mag7` („obchod na Nasdaqu“, sila SPX) sú
predlohy pre NQ, ktoré majú kópie na iné trhy — tam 6 ZAKLAD dáva zmysel ako hypotéza; pri `spravy` je
pravidlo per-správa vyskúmané len na MGC a ZAKLAD_BTC/MNQ… je bez opory.

**N4 (zastarané dokumenty) — počet neplatných základov už nie je 23, ale 10 (po N2 8).**
`docs/audity/2026-11-27-smernica-v2/ZADANIE_IT.md:488` „23 profilov ZAKLAD_6E je neplatných … tks a 12 kópií“,
`PRECITAJ_MA.md:18` „23 profilov“, `KONVERZACIA.md:2534/2541` „924 profilov … 23“. build.py teraz hlási 10:
mag7, tks, tksnet, tksneteod, orb15, mtkorb, mtkorbnet, flashorb, tkseur, tkseurnet. Ak sa necommitne úprava
týchto dokumentov v tom istom commite, IT dostane zadanie U12 so zlým počtom.

**N5 (nesúvisí s opravou) — `tester/audit.json` je zmenený** (`date` 2026-11-08 → 2026-11-26, pribudli
`nocpon`, `noamgc`, `sweepengulf`, `fibomgc` …; 273 riadkov diffu). Nemá s kópiami nič spoločné — necommitovať
v tomto commite bez overenia, odkiaľ zmena je.

**N6 (medzera v smernici) — `SMERNICA_V2.md:257–262` (Krok 3a)** hovorí „východisko na trhu M je ZAKLAD_<M>“,
ale nehovorí, čo s kópiou na cudzom trhu. Po oprave kópia ZAKLAD cudzieho trhu nemá; malo by tam byť výslovne
„kópia sa testuje len na svojom trhu; iný trh = predloha (alebo nová kópia = nová hypotéza, k++)“.

**N7 (drobné) — pravidlo `copy_market` je krehké.** Funguje na prípone a ručnom zozname výnimiek; nová stratégia
končiaca na `…es` / `…eur` (napr. „zones“, „lines“ už boli) dostane jeden profil potichu. Spoľahlivejšie je
výslovné pole v `StrategySpec` (napr. `market=`) alebo `base_key` + trh; `/api/strategies/<k>/meta` už vracia
`base_key`. Neoprava, len nález.

**N8 (overené, bez nálezu) — BTC.** `MK["BTC"] = btcusdt_binance` je perpetuál (`tradebot/core/types.py:440`,
spot je `btcusdt_binance_spot` :442), takže shorty a páka v ZAKLAD_BTC nenarazia na zákaz spotu. NY-seansové
stratégie na 24/7 BTC sú vec hypotézy, nie chyba profilov.

## Kontrola opráv (27. 11., 19:10)

Overené (len čítanie a spúšťanie):
- N1 opravené: `tester/webapp_vyber.json` — v `strategies` aj `dole` 0 odkazov na neexistujúci profil.
- N2+N3 opravené: `build.py` `_ONE_MARKET = {mtkorb, mtkorbnet, spravy, spravynet: MGC}`; kópií je 87.
  `build.py` bez --apply: 489 profilov, neplatných 8 (mag7, tks, tksnet, tksneteod, orb15, flashorb, tkseur, tkseurnet).
  Suchý beh s --apply proti disku: 489 = 489, rozdiel v obsahu 0. Každá z 87 kópií má práve jeden ZAKLAD
  svojho trhu a `default_profile` naň ukazuje; každá iná stratégia má všetkých 6.
  Webapp `/api/strategies/<k>/meta` pre 154 kľúčov = disk (bez reštartu).
- N4 opravené: `ZADANIE_IT.md` U12 bod 1 = 8 profilov s menami, sedí s build.py; `PRECITAJ_MA.md` doplnené.
- N5: `tester/audit.json` je stále zmenený v pracovnom strome — pri commite ho výslovne vynechať (nepoužiť `git commit -a`).
- N6 opravené: krok 3a bod 8 v `SMERNICA_V2.md` aj `docs/SMERNICA_TESTOVANIA.md`. Drobnosť vo formulácii:
  „Iný trh ide cez predlohu“ — `spravy*` sú samy predlohou a na iný trh (okrem 6E = `spravyeur`) predlohu nemajú;
  `mtkorb*` predloha = `orb15`. Nie je to chyba, len to treba vedieť.
- `pytest tradebot/tests/test_config.py`: 39 passed. `ruff check .`: All checks passed.
- Pozor pri commite: 20 nových zmazaní (mtkorb*, spravy*) je v indexe (`D `), 415 starších je len v pracovnom strome
  (` D`) — commit musí zahrnúť oboje (napr. `git add -u tradebot/strategies`).
- N7 (pravidlo podľa prípony): netreba teraz. Generátor je jednorazový audítorský skript a výsledok je overený
  ručným zoznamom; pole trhu v `StrategySpec` je zmena jadra — patrí do zadania IT (U12 ako bod), nie do tohto commitu.

**Verdikt: commitnúť ÁNO** (bez `tester/audit.json`, so všetkými 435 zmazaniami).
