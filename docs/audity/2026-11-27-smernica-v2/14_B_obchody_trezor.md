# 14 — Inžinier B: 150 alebo 300 obchodov v trezore? (27. 11. 2026)

Výpočet: `obchody_sila.py` (presne cez binomické rozdelenie, výplata +W R / −1 R, WR 40–60 %; DD Monte Carlo 20 000 ciest).
Rozsah WR mení výsledky o ≤ 5 p. b., uvádzam WR 50 %.

## 1. Čísla
**Sila = P(t ≥ t_req), jednostranne** (k = 1 → 2,0; k = 20 → 3,0):

| skutočný PF | n 150 | 220 | 300 | 500 | E[t] pri 300 | p (jednostr.) pri 300 |
|---|---|---|---|---|---|---|
| 1,1 | 8 % / 1 % | 10 / 1 | 11 / 2 | 17 / 3 | 0,82 | 0,20 |
| 1,2 | 18 / 3 | 27 / 5 | 34 / 7 | 52 / 17 | 1,57 | 0,058 |
| 1,3 | 34 / 8 | 47 / 16 | 61 / 23 | 83 / 48 | 2,26 | 0,012 |
| 1,5 | 66 / 28 | 84 / 47 | 93 / 66 | 99 / 93 | 3,46 | 0,0003 |

- n na 80 % silu pri t_req 2,0: PF 1,2 → **~1 000**, PF 1,3 → ~480, PF 1,5 → ~200. Pri t_req 3,0: 1 800 / 860 / 370.
  Veta v 8b „pri PF 1,2 treba ~500 obchodov pre t = 2" platí len pre *očakávané* t (sila 50 %) — opraviť.
- **Bez edge (PF 1,0):** P(PF_trezor ≥ 1,2) = 14 % pri 150, 10 % pri 220, 6 % pri 300, 2 % pri 500.
  P(PF ≥ 1,1) = 28 / 23 / 19–22 / 15 %. **P(t ≥ 2,0) = 2,0–2,6 % pri každom n.**
- Pozorovaný PF, ktorý t_req vynúti sám (WR 50 %): n 150 → 1,39 (t 2,0) / 1,65 (t 3,0); n 210 → 1,32 / 1,52;
  n 300 → 1,26 / 1,42.
- Monte Carlo, skutočný PF 1,2: max DD medián / p95 = 10 / 20 R (n 150), 12 / 23 R (220), 13 / 25 R (300);
  90 % interval pozorovaného PF 0,92–1,57 (150) vs 1,00–1,45 (300). Pri PF 1,5: p95 DD 15–18 R.

## 2. Hodnotenie
1. **Pevné 300 nechráni pred falošným ✅ — to robí t.** Falošný poplach t ≥ t_req je ~α pri každom n; PF-brána 1,10
   pri 300 obchodoch pustí stratégiu bez edge v ~20 % prípadov. 300 je teda len druhá, slabšia kópia toho istého testu.
2. **Pri malom n t_req automaticky žiada vyšší PF.** Stratégia, ktorá prejde t 2,0 pri 210 obchodoch (PF ≥ 1,32),
   je rovnako významná ako tá pri 300 (PF ≥ 1,26). Pravidlo 300 ju aj tak zhodí na 🟡 → na MNQ/MYM/BTC/MGC
   pri 75 obch/rok (~210) **nie je ✅ dosiahnuteľné nikdy**, ani pri PF 1,6. To je strata sily, nie opatrnosť.
3. **Prečo nie len t bez minima:** t predpokladá ~nezávislé obchody a nie extrémne chvosty; pri n < 150 sa normálna
   aproximácia pri RR 2 a WR 40 % kazí, odhad PF má interval ±0,3 a jeden zhluk (FOMC týždeň) urobí polovicu t.
   Minimum 150 je ochrana pred malou vzorkou, nie test.
4. **Prop riziko:** DD z trezoru pri malom n podceňuje dlhodobý DD (p95 20–25 R za 150–300 obchodov, za dlhší beh viac).
   Veľkosť sa preto nesmie odvodiť z DD trezoru, ale z MC s **ohaircutovaným** PF. FTMO 10 % = 20 R pri 0,5 %/obchod —
   p95 DD pri PF 1,2 to už vyčerpá. Pravidlo: riziko/obchod ≤ 5 % / p95 DD_R (MC, PF po haircute, n = obchody za 1 rok × 2).
5. **150 ako jediné číslo nestačí na ✅:** pri n 150 je P(PF ≥ 1,2 | bez edge) 14 % a rozptyl PF veľký; preto pre ✅
   vyššie minimum (200), aby trh s 75 obch/rok × 2,8 r ✅ dosiahol, no len s PF ≳ 1,32 (k = 1) až ≳ 1,52 (k = 20).

## 3. Navrhované znenie
**Krok 8b (nahradiť riadky „Dĺžka trezoru" a „PF ≥ 1,10 …"):**
- Trezor ≥ 2 roky a aspoň jeden rok mimo režimu ladenia; kratší alebo jeden režim → najviac ⏳.
- **Obchody v trezore: < 150 → ⏳** (malá vzorka, t sa nehodnotí). Počet nie je brána významnosti, tou je len t.
- **🟡:** n ≥ 150, t ≥ t_req(k), PF ≥ 1,10 s nákladmi §3, ≥ 60 % rokov v pluse.
- **✅:** n ≥ 200, t ≥ t_req(k), PF ≥ 1,15, ≥ 60 % rokov v pluse a žiadny rok pod 0,90, plus veľkosť z MC:
  riziko/obchod ≤ 5 % / p95 max DD v R (PF po haircute §7). Bez MC → najviac 🟡.
- t = priemer R / σ · √n, **jednostranný** test (hľadáme len kladný edge); tabuľka t_req ostáva (2,0 → 3,3), čím je
  jednostranne prísnejšia, než α = 0,05 žiada (1,64) — rezerva na autokoreláciu obchodov.
- Veta „pri PF 1,2 ~500 obchodov" → „pri PF 1,2 treba ~1 000 obchodov na 80 % šancu prejsť t 2,0; pri 210 obchodoch
  t_req vyžaduje pozorovaný PF ≥ 1,32 (k = 1) až 1,52 (k = 20)."
**Krok 4 (výnimka pod 75/rok):** „t_req + 0,5 a ≥ 150 obchodov v trezoroch spolu (✅ ≥ 200)" namiesto 300.
**§1:** stĺpec „čo unesie" pre MNQ/MYM/BTC: „✅ pri ≥ 200 obchodoch v trezore a t ≥ t_req (pri 75/rok ~210 → PF ≳ 1,32)";
MGC (2,7 r): „✅ pri ≥ 75 obch/rok (≥ 200 v trezore) + iný režim + lepší než kúp a drž". Prepočet legacy prahov a C: „< 150 → ⏳", C „≥ 2 roky a ≥ 200".
**§9 bod 1:** „~210 obchodov stačí na 🟡 aj ✅, ak t ≥ t_req; ✅ vtedy znamená pozorovaný PF ≳ 1,32–1,52."

**NÁVRH:** Pevné 300 zrušiť — rozhoduje t ≥ t_req(k) jednostranne; minimum v trezore 150 obchodov (pod → ⏳) pre 🟡, 200 pre ✅ (+ PF ≥ 1,15 a veľkosť z MC p95 DD po haircute), takže ~210-obchodový trezor MNQ/MYM/BTC/MGC môže dať ✅, ale len pri pozorovanom PF ≳ 1,32 (k=1) až 1,52 (k=20).
