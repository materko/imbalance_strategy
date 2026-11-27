# 27 · Prokurátor A · Kontrola opravy ZAKLAD (27. 11. 2026)

**Overené strojovo na všetkých 154 × 6.** `domov.json` sa zhoduje s `25_B` (60 s bodmi, 94 bez_bodov). PRICE_FIELDS má 65 kľúčov, všetky sú v registri a každá stratégia s domovom ≠ bez_bodov ho má.
Všetky profily sa načítajú, jednotky SizeSpec sedia so SIZE_FIELDS a ticks polia sú int. Pri 1224 aktívnych cenových poliach je efektívna cena na M voči ATR prepočtu mimo ±50 % v 85 prípadoch. Všetkých 85 má poznámku, alebo je profil NEPLATNÝ.

- **C1 vyriešené.** Poznámka ostáva aj vtedy, keď sa výsledok rovná defaultu (ibs ES/MYM/MGC/6E state2ConfirmTicks +110 až +529 %, m2 6E).
- **C2 vyriešené.** voltbreak ES TP/SL 7,5/13,75 b, MGC 5,5/10,4, BTC 269/504. usdPerPoint sa naozaj používa len v tp/sl_points (py aj C#).
  **Tvrdenie B je však nepravdivé:** „6E by aj tak padla na rozsahu“. Pri usdPerPoint=1000 (v rozsahu, PORT_ONLY) vyjde tpUsd 1,25 $ a slUsd 2,4 $ (≥ 1), čo je TP 25 t a SL 48 t. 6E je teda platná bez zmeny kódu a označenie NEPLATNÝ je zlé.
- **C3 vyriešené.** mag7 slOpenBuf ES 0,25, MGC 0,3, BTC 13,5, 6E 1 t (+28 %).
- **C4 vyriešené.** Prešiel som všetky číselné a SizeSpec polia so sprostredkom ≠ 0 vo všetkých 154 configoch. Žiadne cenové pole nechýba.
  Zvyšok sú ATR/%/R násobky, časy, bary a sizing v $ (`maxLossDollar` je riziko, nie prah ceny). Polia s defaultom 0 sú pre ZAKLAD neaktívne.
- **C5 neúplné.** Zoznam berie len vybrané mená. Vynechal tieto predvolene zapnuté časové výstupy so spínačom: `fpc.useCloseAfter` (zavretie 30 min po okne, rovnaký typ ako `useTimeExit`, ktoré v zozname je),
  `dailyopen/dailyopenbtc.useExit` (16:00), `asiasweep/asiasweepeur.useExitTime` (12:00) a `nqprec/nqpreces/nqprecmgc.useTimeClose`. Je to 8 stratégií a 48 profilov bez vety §0.
  **Odpoveď na otázku B:** `useCloseAfter` áno. `ivb.eodFlatten` nie: je to len čas, spínač je `flattenEod` a ten je predvolene False (ivb správne bez vety).
  Pevné časové výstupy bez spínača sa vypnúť nedajú: silverbullet×3 exitH 15:55, sweepfvg, nyvaes×2 closeH 15:59, vwapop flatTime, onbiasorb exitHHMM.
  Do `_comment` pre ne patrí veta „koniec seansy je v kóde bez prepínača, hlavička ho prijme ako logiku hypotézy“. Inak §0 visí.
- **C6 čiastočne.** Domov, istota, pomer a obdobia sú v `_comment`. Pomer ATR je ale z **rôznych období** jednotlivých trhov, čo dáva systematickú chybu.
  ES/MNQ teraz vychádza 0,185, v spoločnom období MNQ L (2019-05 až 2022-09) 0,241 (−23 %). MGC je o +31 %, 6E o +7 %.
  Je to pod prahom 50 %, ale všetky prahy ES sú o štvrtinu užšie a prahy MGC o tretinu širšie. Text 3a(5) to dovoľuje, ale to je diera v smernici, nie alibi.

## NÁLEZY pre B
1. `voltbreak/configs/ZAKLAD_6E.json`, `voltbreaknet/configs/ZAKLAD_6E.json`: tpUsd, slUsd, usdPerPoint. Treba usdPerPoint=1000, tpUsd=1,25, slUsd=2,4 a zrušiť NEPLATNÝ (neplatných základov bude 23, nie 25). Opraviť aj vetu v 26_B.
2. `build.py:EXIT_FLAGS`: pridať `useCloseAfter`, `useExit`, `useExitTime` a `useTimeClose`. Pregeneruje to fpc, dailyopen(btc), asiasweep(eur) a nqprec(es, mgc).
3. `build.py`: veta o pevnom konci seansy bez prepínača pre silverbullet(eur, btc), sweepfvg, nyvaes(net), vwapop a onbiasorb(btc) (`exitH/closeH/flatTime/exitHHMM`).
4. `atr.py` / `atr.json` + 3a(5): pomer ATR počítať v **spoločnom okne** domova a M (prienik dát), nie z L každého trhu. Kým sa to neopraví, zapísať do `_comment` aj odchýlku (ES −23 %, MGC +31 %).
