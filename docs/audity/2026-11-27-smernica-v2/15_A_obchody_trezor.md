# 15 — Prokurátor A: odpoveď na 14_B (150/200 namiesto 300) — 27. 11. 2026

## 1. Overenie
`obchody_sila.py` som spustil (`.venv/bin/python -I`): **všetky čísla v 14_B sedia** (sila, n na 80 %, PF pod nulou, MC DD, PF z t_req).
Model je však ideálny: ±R, iid, jedna kópia. Doplnková simulácia (40 000 ciest, nulová stratégia, P(t ≥ 2,0) / P(t ≥ 3,0); nominálne ~2,3 % / 0,13 %):

| porušenie modelu | n 150 | n 210 | n 300 |
|---|---|---|---|
| záporná šikmosť (WR 75 %, malý TP, 4 % gapov −3 R) | 3,9 / 0,65 % | 3,6 / 0,52 % | 3,4 / 0,38 % |
| kladná šikmosť (trend, WR 35 %, exp. výhry) | 1,2 / 0,02 % | 1,3 / 0,03 % | 1,4 / 0,03 % |
| zhluky (bloky 10 obchodov s posunom σ 0,25 R) | 5,4 / 0,80 % | 5,5 / 0,86 % | 5,3 / 0,80 % |
| 6 kópií na trhoch (ρ 0,6), každá k = 1, n 210 | rodina 9,8 % | (ρ 0: 12,8 %) | |

- **Autokorelácia** zdvojnásobí falošný poplach pri t 2,0 a pri t 3,0 ho zväčší ~6×, **pri každom n**. Rezerva „jednostranne s tabuľkou“ ju nepokryje. Pevné 300 ju tiež nerieši.
- **Skutočné rozdelenie R:** pri zápornej šikmosti (naše WR 70–100 %, RR 0,5) **n záleží**: chyba pri t 3,0 je 5× pri 150 a 3× pri 300. Tu je argument B „počet nie je brána“ chybný. Kladná šikmosť (trailing, EMAS) je naopak konzervatívna.
- **Kópie (…btc, …eur, …mgc, …mym):** t_req počíta k na trezor, nie na rodinu. Šesť trhov s k = 1 dá ~10–13 % falošných ✅. Veta kroku 4 „≥ 150 obchodov v trezoroch **spolu**“ dovoľuje sčítať MNQ+MYM+ES (ρ ~0,9), čo je pseudoreplikácia.
- **Prekliatie víťaza:** pri skutočnom PF 1,3 a n 210 prejde t 2,0 len 47 % ciest a ich medián PF je **1,43**. Pri t 3,0 prejde 12 % s mediánom **1,60**. MC veľkosť z pozorovaného PF teda nadhodnocuje edge o 0,13–0,30.
- **Tučné chvosty a DD:** MC 14_B je iid ±R. Zhluky a gapy predĺžia p95 DD. Denný limit FTMO 5 % (súbežné kópie v jeden deň) sa nekontroluje vôbec.
- Drobnosť: tabuľka t_req je Bonferroni **obojstranne** (k 20 → 3,02). Prechod na jednostranný test je v poriadku, ale nie je to „rezerva na autokoreláciu“.

## 2. Bod po bode
1. 300 nie je test významnosti, je ním t — **súhlas** (pri iid, ±R).
2. Malé n si samo vynúti vyšší PF — **súhlas**, ale len po korekcii t (bod 1 vyššie).
3. 150 ako ochrana malej vzorky — **súhlas** pre 🟡. Pre ✅ pri zápornej šikmosti **nesúhlas** (pozri tabuľku).
4. Veľkosť z MC p95 po haircute — **súhlas v princípe, nesúhlas s vykonaním**: iid MC a bez korekcie prekliatia víťaza.
5. ✅ od 200 — **podmienený súhlas** (doplnky nižšie).
6. Oprava vety „PF 1,2 ~500“ — **súhlas**.

## 3. Protinávrh (doplnky k znenia B)
- **t = min(t_obchody, t_mesiace)**, kde t_mesiace sa počíta z mesačného PnL trezoru (≥ 24 mesiacov), prípadne HAC Newey-West s lagom 5 obchodov. Tabuľka t_req ostáva.
- **Šikmosť R v trezore < −1** (malý TP, gapy): pre ✅ n ≥ 250 a t_req + 0,3; pre 🟡 platí 150.
- **Rodina kópií:** k = súčet hypotéz cez **všetky trhy rodiny** (≥ 6 kópií → k ≥ 5, t_req ≥ 2,6). Obchody sa **nesčítavajú** cez trhy s ρ mesačného PnL > 0,5; n je za trh.
- **Veľkosť:** PF_MC = 1 + (PF_obs − 1) / 2, kým n < 300 (inak haircut §7). MC ako **blokový bootstrap mesačných blokov** obchodov z trezoru, nie iid ±R. Riziko ≤ 5 % / p95 DD_R a zároveň p99 denná strata všetkých súbežných kópií ≤ 4 %.

**DOHODA:** Pevné 300 zrušiť; rozhoduje t ≥ t_req(k) jednostranne, kde **t = min(t z obchodov, t z mesačného PnL)** a **k sa počíta cez celú rodinu kópií na všetkých trhoch**. Obchody sa medzi trhmi s ρ > 0,5 nesčítavajú. Pod 150 obchodmi za trh je výsledok ⏳, 🟡 je od 150, ✅ od 200 (pri šikmosti R < −1 od 250 a t_req + 0,3) s PF ≥ 1,15. Veľkosť sa určí z blokového MC s PF_MC = 1 + (PF_obs − 1)/2 (n < 300) a s kontrolou dennej straty FTMO. Bez týchto doplnkov trvám na 300 pre ✅.
