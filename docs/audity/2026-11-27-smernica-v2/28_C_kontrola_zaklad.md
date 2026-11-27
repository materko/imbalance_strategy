# 28 · Kontrolór C · Finálna kontrola ZAKLAD (27. 11. 2026)

**Strojovo, 924/924 profilov:** všetky sa načítajú, `_instrument`/`_timerange` = MK, tick inštrumentu = TICK v build.py (MNQ/ES 0,25, MYM 1, MGC 0,1, 6E 0,00005, BTC 0,1).
Mimo PRICE_FIELDS (+ usdPerPoint) sa nezmenilo ani jedno pole voči defaultu, takže logika je nedotknutá. Ticky sú int. Každá odchýlka efektívnej ceny > 50 % od default × pomer má poznámku s % alebo je profil NEPLATNÝ.
NEPLATNÝCH je 23, všetky na 6E (tks ×13, orb15/mtkorb ×5, flashorb ×4, mag7). pytest (4 súbory): **70 passed**.

- **C1–C4, A1, A2: vyriešené.** Skenoval som číselné a SizeSpec polia ≠ 0 vo všetkých 154 configoch. Zvyšné kandidáty sú R násobky, bary a časy, cenové pole nechýba.
- **A1 voltbreak 6E** 1,35/2,5 $ pri usdPerPoint 1000 (27/50 t) sedí. `usdPerPoint` sa číta len v `tp_points`/`sl_points` (py) a `TpPoints`/`SlPoints` (C#), inde v repe nie je. Logika sa preto nemení.
  Kozmetika: webapp ukáže „USD za bod 1000“ a TP 1,35 $, čo pri 6E nie sú skutočné doláre (125 000 $/bod).
- **A3 (B: „každý časový výstup má prepínač“): pre vymenované stratégie pravda.** silverbullet/sweepfvg `useExitTime`, nyva(es) `useCloseTime` (py aj C#), vwapop `closeEOD`, onbiasorb `useTimeExit`.
  **Ako všeobecné tvrdenie je to nepravda (nový nález N1):** `noa/engine.py:126` a `NoaEngine.cs:229` zatvárajú o 16:00 napevno, bez spínača. To platí pre 11 kľúčov noa*.
  Päť kópií `*eod` (ibsentryneteod, noaneteod, tksneteod, vwapadxneteod, vwaporbneteod) zatvára o 15:59 cez `EodCloseEngine`, tiež bez spínača.
  `FIXED_EXITS` je prázdny, takže 15 kľúčov × 6 = 90 profilov nemá vetu o pevnom konci seansy. Napr. `tksneteod/ZAKLAD_ES` nemá žiadnu vetu §0, noa má len `trailVwap`.
- **A4 pomer ATR: číslo je správne.** Môj prepočet na zarovnaných dňoch (jednoduchý / Wilder ATR, deň UTC aj CME +7 h):
  MNQ→ES 0,236–0,239 (build 0,2396), MNQ→MGC 0,102–0,103 (build 0,1033). Medián denných pomerov dáva MGC 0,116–0,120 (+13 %), je to však pod prahom.
- **Nový nález N2 (trezor v okne).** MNQ↔MGC a 6E↔MGC nemajú prienik L, preto atr.py berie prienik celých dát (2019–2026, resp. 2010–2026).
  To sú aj trezorové roky (MGC 2020–22, MNQ 2022-10–2025-09, 6E 2021-10+) a spálený rok. Ide o 56 profilov, ktorých prahy sú odvodené aj z trezoru a spáleného roka. Je to slabá informácia (len volatilita), no §1 chce „trezor mimo období štúdií“.
  Čisté spoločné okno pre MNQ–MGC neexistuje (MGC L 2023+ = MNQ trezor).

## VERDIKT: commitnúť **nie** (zatiaľ). Obe opravy sú malé, potom áno bez ďalšieho kola.
## NÁLEZY pre B
1. `build.py:FIXED_EXITS`: pridať 11 noa* (`_CLOSE_MIN` 16:00) a 5 *eod (`EodCloseEngine` 15:59) a pregenerovať. Opraviť vetu v 26_B kolo 2/3 („FIXED_EXITS prázdny“).
2. `atr.py`: pre páry bez prieniku L nepoužiť celé dáta. Buď vziať každý trh na vlastnom L s normalizáciou ATR/cena × cena_M na L_M, alebo `pomer_rozne_L`, a zapísať to do `_comment`.
   Inak výnimku výslovne zapísať do 3a(5) so súhlasom používateľa.
3. (nepovinné) `_comment` voltbreak 6E: pripísať, že „$“ pri usdPerPoint 1000 nie sú skutočné doláre 6E.

## Kolo 3 (po 26_B kolo 3)
- Strojová kontrola na 924 profiloch je bez chyby. Logika je nezmenená, ticky sú celé čísla a odchýlky nad 50 % majú poznámku. Neplatných je 23, všetky 6E. pytest: 70 passed.
- **N1 vyriešené.** `FIXED_EXITS` má 15 kľúčov, takže 90 profilov má vetu o pevnom konci seansy. `EodCloseEngine` používa práve 5 enginov *eod a noa engine nededí nikto mimo noa*. Nič nechýba.
- **N2 vyriešené.** MNQ↔MGC aj 6E↔MGC majú pomer z vlastného L každého trhu a trezor ani spálený rok do výpočtu nevstupujú. Ostatné páry ostávajú na spoločnom L.
  Daň za to: MNQ→MGC je 0,1379, kým v spoločných dňoch vychádza 0,103. Prahy MGC sú tak asi o +33 % širšie, čo je pod prahom 50 %. Je to zapísané v `_comment`, preto to prijímam.
- **N3 vyriešené.** voltbreak(net) 6E má vetu, že „$“ nie sú skutočné doláre 6E. Hodnoty 1,35/2,5/1000 sú nezmenené.
- Nová chyba nevznikla.

**VERDIKT kolo 3: commitnúť ÁNO.**
