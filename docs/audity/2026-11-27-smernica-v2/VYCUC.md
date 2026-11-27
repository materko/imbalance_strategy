# Výcuc — debata agentov + náš rozhovor (26. 11. 2026)

## Náš rozhovor (používateľ ↔ Mac mini)
- Štúdia kĺzavých priemerov hotová (KLZAKY-STUDIA), koncepty K1–K6 v KONCEPTY.md — **nič nepostavené**. Kriticky: neporovnané
  s kúp a drž, dvojitý výber (vstup × výstup), 18–50 obch/rok, bez swapu a gapov → čakať PF o 20–40 % nižší.
- Od dnes: kritický režim, bez lichotenia, stručne (uložené v pamäti).
- MacBook už nahral SMERNICA_TREND_CFD.md a OOS-STARE-ROKY (staré roky: väčšina profilov neobstála).
- Zadanie agentom: celý systém (smernica, automat, výsledky, webapp, živé účty), ťažisko preoptimalizovanie;
  dve otázky: **(1) ako testovať, aby naživo prišlo to isté, (2) zarába niečo naozaj?**

## Kolo 1 — Inžinier (B): čo hovorí literatúra
- Naše hľadanie: **1,55 mil. kombinácií** (TKS 82 tis.). MinBTL (Bailey a kol. 2014): na 5 rokoch ~45 nezávislých variantov.
- „Odložený rok raz“ pustený **1 965×** a podľa neho sa vyberá → je to in-sample.
- DSR sa počíta, prah 0,95 nesplní nikto (najlepšia 0,93, NOA 0,33), ale nebrzdí. Test proti náhode nekoriguje výber z N.
- Smernica čaká zrážku 20–30 %, literatúra 50–73 % (Suhonen 2017). Štat. sila OOS: PF 1,2 pri 150 obch. = t ≈ 1 (nič nedokazuje).
- Chýba: register pokusov, DSR/PBO ako brána, Reality Check/SPA, walk-forward ako hlavný test, sklz v ladení,
  iné podkladové aktívum (NQ→NAS100 nie je iný trh), P(ruina) pri limitoch FTMO.
- Silné: krok 1 (naživo = história), C# parita, kontrola dát.
- Návrh brány: register N → walk-forward PF ≥ 1,15, WFE ≥ 0,5 → DSR ≥ 0,95 / PBO ≤ 0,2 → nevidené roky raz, t ≥ 2
  → iné aktívum → P(ruina) ≤ 5 % → paper.

## Kolo 1 — Prokurátor (A): obžaloba A1–A20
- **Výber:** ~1,8 mil. pokusov (+ hyperopt), odložený rok > 2 300 behov, `gldash.py:480` zoraďuje podľa OOS PF a top 3 → webapp/LIVE.
- **Medián kandidátov na OOS ≈ 1,0** (TKS 1,03, VWAP ORB 1,01, NY VA 1,01, IVB 0,97, NOA MGC 0,84) — do webapp idú chvosty 1,5–1,8.
- IBS EZ: +8,5 σ a trieda A, na starých rokoch **0,79 (0/3)** → jeden odložený rok meria režim, nie edge.
- Plató len ±1 krok jednej skupiny, bool/str parametre netestované; optimum je v ~20 rozmeroch.
- Dve verzie smernice (repo 150 obch tvrdo, automat 75), počet obch len priemer, nie každý rok.
- SPRÁVY MGC/EUR: PF ~4, pravidlá z celého obdobia, staré roky neoverené, MGC beží naživo.
- Ladenie po živej strate: filter špičky volatility IBS EZ 11 (24. 11.) na novembri.
- **Náklady/fill:** poplatok % z ceny → MGC ~0,3 ticku, 6E ~0,37 (repo model 1,5 / 1). Limit a TP pri dotyku, stop bez sklzu;
  profily RR 0,5 / WR 74 % majú rezervu len 7–9 p. b.
- **Naživo:** ~−5 740 $ za 6 týždňov; NOA −2 489 $ > MC DD95 ~2 100 $ a beží; WR naživo 21 % vs 41 %, zhoda 13/17.
- 3 Nasdaq stratégie naraz na FTMO = jedna stávka; v EA žiadny denný stop účtu ani trailing DD.
- **Zarába niečo?** Dôkaz nemá nič. Kandidáti na forward: Noc+pondelok (MNQ, MYM), ON bias ORB, Williams R 6E, NOA (po oprave
  exekúcie), Volt Break, ORB 15/5 ES (tenké). Mŕtve: IBS EZ, TKS, VWAP ORB, NY VA, IVB, NOA MGC, Sigma MGC/MYM, CRT, … —
  tri z nich bežia/bežali naživo.

## Kolo 2 — Inžinier (B): overenie obžaloby
- Verdikty: **13 platí, 7 čiastočne, 0 neplatí.** Tabuľku mediánov OOS a 1,79 mil. pokusov prepočítal a potvrdil.
- Opravy A: IBS EZ na MNQ má prahy v bodoch (2019–21 iná cenová hladina) → čistejší dôkaz je IBS EZ ES 3/12 rokov a MYM 0,79.
  NOA WR 4/19 je náhodou možné na ~6 % (podozrivé, nie dôkaz); MC DD na inej veľkosti. Tri DD čísla = tri definície.
  MNQ poplatok dnes ~1,7 ticku (OK), podhodnotené sú staré roky, MGC/6E/ES.
- Horšie, než A písal: **SPRÁVY profil_3 ~40–50 parametrov na ~36 obch/rok; NFP vstup v čase správy** — na FTMO funded
  zakázané 2 min okolo správy (typ účtu Server3 neznámy, overiť pred NFP). Na Server3 **9 inštancií**, aj US500 (korelácia ~0,9).
  Živé účty sú CFD → futures model nákladov tam neplatí, merať zo skutočných plnení.
- Nové: B1 aj triedenie 44 stratégií na starých rokoch je viacnásobný test (~5–7 falošných ✅ z náhody, váhu má len t ≥ 3);
  B2 bodové prahy znehodnocujú test na iných rokoch; B3 **4. 9. – dnes je zadarmo nevidené obdobie**;
  B4 pásmo WR 70–100 % = ladenie na winrate, tlačí do RR 0,5 kde fill klame; B5 aj výber stratégií je pokus; B6 chýba ruina na portfóliu.
- **(a) Nový proces:** trezory A (9/25–9/26, spálený), B (staré roky), C (9/26+ a demo) — každý raz na stratégiu, nikdy na poradie;
  register pokusov, rozpočet ≤ 200 konfig. a ≤ 5 parametrov; náklad v tickoch + 1 tick sklz, limit/TP až pri prechode o tick,
  zrušiť cieľ WR; walk-forward 24/6 (PF ≥ 1,15, WFE ≥ 0,5, 3/4 kúskov +); PBO ≤ 0,2, DSR ≥ 0,95, haircut na stránke;
  t ≥ 2–3 a ≥ 300 obch v trezoroch; bootstrap portfólia P(denná 5 %) ≤ 2 %, P(DD 10 %) ≤ 5 %; denný stop v EA;
  demo 8 týždňov / 40 obch, zhoda ≥ 95 %. Očakávanie: prejde PF 1,25 → naživo 1,1–1,25, nie 1,5–1,8.
- **(b) Zarába?** Nie s dôkazom. Najsilnejšie: Williams R Long 6E (t ≈ 4,1), Noc + pondelok MNQ (t ≈ 3,0, počet pokusov neznámy),
  NOA/NOA EOD len na papieri (exekúcia 13/17). Slabé: ON bias ORB, Volt Break, Daily open. ORB 15/5 ES → mŕtve.
  **Odporúča zastaviť naživo TKS, IBS EZ 11 a SPRÁVY**, nechať len demo.

## Kolo 3 — Prokurátor (A): replika
- Prijíma: bodové prahy IBS EZ, MNQ náklad dnes ~1,8 ticku OK, rôzne veľkosti naživo, A17/A19.
  Ale ES je ešte viac skreslené (cena 5× vs MNQ 2×) → IBS EZ „neobhájená“, nie „mŕtva“; pre live to isté — nie.
  Bez skreslenia bodovými prahmi ostáva len Williams R 6E.
- Diery v návrhu Inžiniera: **rozpočet sa obíde kópiou stratégie** (rodina Williams R spolu 76 352 kombinácií) → 300 pokusov
  na hypotézu cez všetky trhy a verzie; mriežky a metódu efektívneho N zmraziť commitom vopred; obdobie 9/2026–dnes je
  znečistené rozborom novembra (na exekúciu áno, na edge až dáta od 1. 12.); riziko propky z equity cez MAE
  (P denný ≥ 4 % ≤ 2 %, celkový ≥ 8 % ≤ 5 %); pri PF 1,2 treba ~500 obch na t = 2 → stiahnuť NQ 2010–2019; indexy USA nie sú nezávislé.
- Zhoda: Williams R 6E kandidát; TKS, VWAP ORB, NY VA, IVB mŕtve. **Spor:** NOA (B kandidát, A pozastaviť: DSR 0,33, t ≈ 1,9,
  naživo 4/19), ORB 15/5 ES (A: 1 tick už bol v starých rokoch). Noc+pondelok a ON bias ORB: neznámy pôvod (0 kombinácií v automate).
  Rozhodujúce testy T1–T5 s hranicami vopred.
- **Okamžite (do NFP 4. 12.):** zistiť, či je FTMO-Server3 výzva alebo funded; dovtedy pozastaviť SPRÁVY profil_3;
  pozastaviť TKS a IBS EZ 11, NOA do testu T3; pred zapnutím denný stop účtu (−2 % equity, celkovo −6 %). Rozhoduje používateľ.
- Neskôr: inventúra prevádzky (Tradeify stojí od 19. 11., duplicity), stop ladenia na okt/nov, webapp neradiť podľa OOS,
  preč „posl. rok PF“ z titulov, jedna smernica, fill pri prechode, náklad v tickoch, register, DSR/PBO brány, NQ 2010–2019.

## Kolo 4 — Inžinier (B): odpoveď + návrh SMERNICA_V2
- Oprava oboch: **Williams R 6E sa ladila na 2016–9/2021** → jej „staré roky“ sú in-sample; Noc + pondelok tiež (prieskum MNQ 2019–2026).
  IBS EZ ES má prahy v ATR → jej 0,75 je čistý negatívny dôkaz.
- NOA má pôvod v článku (Zarattini a kol. 2024) → test T6: verzia podľa článku bez zmeny.
- SMERNICA_V2 (14 krokov): trezory s dátumami (čisté len NQ/YM/GC 2010–2019 a dáta od 1. 12. 2026), register a 300 konfigurácií
  na hypotézu, ≤ 5 parametrov, náklady v tickoch a fill pri prechode, walk-forward 24/6, DSR/PBO/haircut ako brány,
  portfólio z equity, stop účtu −2 % / −6 % v kóde, demo 8 týždňov / 40 obch, webapp bez „posl. rok PF“.

## Kolo 5 — Prokurátor (A): pripomienky k V2
- Nové tvrdenia Inžiniera overil — sedia. **Zhoda: dnes nemáme ani jeden čistý pozitívny dôkaz.**
- Diery: hypotézy po jednej obídu t_req → počítať kumulatívne; walk-forward zamknúť; bonus za ekonomický dôvod len s vonkajším
  zdrojom; spread CFD sa zo zrkadla zmerať nedá → logovať v EA; chýba trailing DD (Tradeify) a strop súčasného rizika 1,5 %.
- NOA podľa článku: čisté je len obdobie po publikácii (MNQ od 6/2024).
- DOHODY: min. 100 obch v každom roku (výnimka vopred, prísnejšia); ladená NOA ⚠; ORB 15/5 ES najviac ⚠; stop účtu −2 %/−6 %.
  SPRÁVY: ekonomický dôvod uznáva, ale > 5 parametrov → ⚠, návrh „SPRÁVY-jadro“ s ≤ 5 parametrami; DSR prepočítať s N ≈ 2 500.
- Doplniť: jedna smernica v repe, max 10 hypotéz/štvrťrok, ✅ len skriptom z registra, CFD replay pred demom, prechody stavov
  podpisuje používateľ, ochrana účtu lokálne bez hubu, vypnúť ranné `glwebvyber --apply`, kým radí podľa OOS.

## SPRÁVY na starých rokoch 2010–2021 (Mac mini, nastavenia nezmenené)
- Kalendár z ForexFactory (1 937 správ), na 2021–2025 sedí so smernicovým na 100 % dní.
- **Profil 1–3: PF ~1,0, 5–7 z 11 rokov v pluse** (+0,8 k / +1,9 k / +7,0 k $ za 11 rokov) proti PF 3–7 v rokoch 2021–2026.
- **S nákladom 1,5 ticku všetky tri v strate** (−10,4 k / −8,6 k / −37,2 k $). Okno 2020/21 (dobré dáta) tiež v strate.
- Záver: pravidlá sedia na 2021–2026; mimo nich edge nie je. Obhajoba „inflačný režim od 2021“ = edge viazaný na režim.
  Podrobne iCloud SPRAVY/vyskum/STARE_ROKY_2010_2021.md.

## Kolo 6 — Inžinier (B): dohodnutá SMERNICA_V2 + záver
- Prevzal všetky pripomienky Prokurátora; SMERNICA_V2 = dohodnutá verzia (14 krokov, trezory A/B/B′/C, prechodné pravidlá P1–P8,
  testy T1–T6, stav každej stratégie, 5 otázok pre používateľa v §9, zavedenie 5–7 týždňov, najprv ochrana účtu).
- SPRÁVY legacy profily preradil na ❌ (trezor B); otvorená len nová hypotéza „SPRÁVY-jadro“ s ≤ 5 parametrami.
- Záver: ani jedna stratégia s čistým pozitívnym dôkazom; najbližšie Williams R 6E, NOA podľa článku, Noc + pondelok.

**Celkový sumár: SUMAR.md.**

**Používateľ (26. 11.):** náš FTMO účet smie obchodovať správy → bod o NFP T+0 a pravidle FTMO padá; ostáva len preladenie SPRÁVY.

**Používateľ (26. 11.):** schválil Sortino len z walk-forward OOS a trezorov (≥ 1,0, aj portfólio); trezor aspoň 2 roky + ≥ 300 obchodov + aspoň jeden iný režim — doplnené do SMERNICA_V2 (krok 7, 8b, 11).

## Kolo 7 — Inžinier (B): rozdelenie dát (Databento + BTC)
- Zmeral sám (`dq_scan.py`, `data_kvalita.json`). Čisté: **ES 6/2010+** (pokrytie 98–99,5 %, najlepší), **MNQ 5/2019+, MYM 6/2019+**
  (~98,5 %), **MGC až 2020+** (2010–15 pokrytie 8–39 %, 2016–19 64–92 %), **6E 2016+** (2010–15 220–636 zlých tikov/rok).
  Rolovanie bez back-adjustu skáče 0,3–0,9 % (max 2,1 %) — stratégie s dlhými priemermi potrebujú vyradiť dni rolovania.
- **BTC: Binance futures perp** 9/2019–9/2026 (99,3–100 %, 0 dier, skutočný objem, funding). Spot len kontrola;
  Dukascopy bez objemu od 2021 a s dierami; Coinbase 1 mesiac.
- Návrh: **ES** ladenie 6/2010–9/2018 (8,3 r.), trezor B 10/2018–9/2021 (3 r., Q4 2018 + covid), B2 10/2021–9/2025 len pre
  rodiny, ktoré tam nebežali, 2025/26 spálený, C od 1. 12. 2026. Rovnaká schéma pre MNQ/MYM/MGC **až po stiahnutí NQ/YM/GC 2010–2019**.
  6E: ladenie 2016–9/2021, B′ = 2010–15 po vyčistení tikov. BTC: ladenie 10/2021–9/2025, B 2019–21 len 2,1 roka (< 300 obch).
- Dnešné stratégie nemajú okrem C čistý trezor. Pri 100 obch/rok pravidlo „2 roky + 300 obchodov“ = reálne 3 roky.

## Kolo 8 — Prokurátor (A): rozdelenie dát
- Meranie prepočítal na 7 súboroch — sedí. Chýba meranie **nočného okna** (nocpon, ON bias, sweep).
- **Protinávrh: jeden rad na trh, nie zošívanie** — stiahnuť NQ, YM, GC 2010–dnes, mikro len na exekúciu (objem NQ vs MNQ
  rozbije VWAP / objemové stratégie). Bez toho Nasdaq, Dow a zlato nemajú čistý trezor.
- Nové hypotézy: **ladenie 2010–9/2017, trezor 10/2017–9/2021** (4 roky, ~400 obch, Volmageddon, Q4 2018, covid).
  6E súhlas (čistenie len skokov, čo sa do minúty vrátia ≥ 80 %, mimo ±3 min od správ). BTC len perp: ladenie 9/2019–9/2023,
  trezor 9/2023–9/2025, len pre stratégie ≥ 150 obch/rok.
- **Rolovanie vadí aj intraday:** PDH/PDL, gap, denné ATR, dlhé SMA sú v deň rolovania posunuté (MNQ ~200 bodov, 4× ročne)
  → `rolls.json`, back-adjust pre indikátory naprieč dňami, dovtedy `skipRoll`; overiť prepínanie kontraktov tam a späť.
- Dnešné stratégie najviac 🟡. „Iný režim“ merať vopred (štvrťrok s ATR mimo rozpätia ladenia alebo pokles > 15 %).
  Trezor C dopĺňať z rovnakého zdroja (Databento, Binance perp), nie zo sviečok hubu.

## Kolo 9 — Inžinier (B): dohoda o dátach (zapísaná do SMERNICA_V2 §1)
- Prijal všetkých 7 bodov Prokurátora; doplnil: objemové prahy len relatívne, prahy legacy pomerom ATR(14).
- Nočné pokrytie (`dq_night_rolls.py`): MNQ a ES 96–100 %; **MYM noc 2019 86,5 %, 2024 94,8 %** → nočné Dow stratégie potrebujú YM;
  6E noc 2013–15 85–95 %; MGC pred 2020 v noci 2–80 %.
- Rolovanie: MNQ, MYM, ES, 6E presne 4× ročne bez návratov; **MGC 1/2011 prepína tam a späť** → MGC pred 2020 nepoužiteľné.
- **Finálne rozdelenie (nové hypotézy):**

| trh | ladenie | trezor | spálený | demo |
|---|---|---|---|---|
| ES, NQ, YM | 6/2010 – 9/2017 (~730 obch) | 10/2017 – 9/2021 (~400) | 4. 9. 2025 – 3. 9. 2026 | od commitu hraníc |
| GC | 10/2010 – 9/2017 | 10/2017 – 9/2021 | to isté | to isté |
| 6E | 2016 – 9/2021 | 2010–2015 po vyčistení | to isté | to isté |
| BTC (Binance perp) | 9/2019 – 9/2023 | 9/2023 – 9/2025 (len ≥ 150 obch/rok) | to isté | to isté |

  Legacy: trezor len NQ, YM, GC 2010–2019, inak C. Mikro kontrakty len na exekúciu.
- **Bez stiahnutia NQ, YM, GC sa nové hypotézy na Nasdaqu, Dowe a zlate nespúšťajú.** Rozhoduje používateľ.

**Používateľ (26. 11.):** schválil rozdelenie rokov len z dát, ktoré máme (ES, 6E, MNQ, MYM, BTC, MGC — tabuľka v SMERNICA_V2 §1), a že sa takto testuje vždy.

## Kolo 13 — A k rozdeleniu z dát, ktoré máme
- Návrhy: trezor mimo období štúdií, z ktorých hypotéza vznikla; jedno rozdelenie na trh; MGC a 6E obrátiť; ES trezor 2010–2014.
- **Čaká na používateľa** (odporúčanie: 1–3 áno, 4–5 nie).

**Používateľ (26. 11.):** stačí ≥ 75 obchodov za rok. Pýta sa, prečo trezor chce 300 obchodov, a nie 150. „Ako sa rozhodnú agenti, čo je lepšie, to tam dáme.“

## Kolo 14 — B: koľko obchodov v trezore
- Pred náhodou chráni t, nie počet obchodov. Stratégia bez edge má t ≥ 2 v ~2–2,6 % prípadov pri každom n; pevné 300 je len slabšia kópia toho istého testu.
- 300 by na MNQ, MYM, BTC a MGC (~210 obchodov) zakázalo ✅ aj pri PF 1,6.
- Návrh: 300 zrušiť; < 150 ⏳, 🟡 od 150, ✅ od 200 + PF ≥ 1,15 + veľkosť z Monte Carlo.

## Kolo 15 — A: kontrola
- Čísla B sedia, ale model je ideálny. Zhluky obchodov zdvojnásobia falošný poplach a záporná šikmosť (vysoký WR) ho zvýši 3–5×.
- Kópie na viacerých trhoch sa nesmú sčítať; víťaz preceňuje edge (pri skutočnom PF 1,3 je medián pozorovaného 1,43–1,60).
- Denný limit FTMO 5 % pri súbežných kópiách sa nekontroloval.
- **Dohoda (zapísaná do V2, krok 8b):** 300 zrušené.
  - t = min(t z obchodov, t z mesačného PnL); k cez celú rodinu kópií.
  - Prahy na trh: < 150 ⏳, 🟡 od 150, ✅ od 200 a PF ≥ 1,15; pri šikmosti < −1 od 250 a t_req + 0,3.
  - Veľkosť: blokové MC s PF po polovičnom haircute; p99 dennej straty kópií ≤ 4 %.

**Používateľ (27. 11.):** zastaviť všetky testy na hube — zastavené, pauza `gl_paused`.

**Používateľ (27. 11.):** „všetko, na čom sme sa dohodli, pridať do smernice“. Zapísané z kola 13:
- jedno rozdelenie na trh bez variantov;
- trezor mimo období štúdií (hlavička vymenuje štúdie, inak automat nepustí; inak najviac 🟡);
- MGC obrátené: ladenie 2023 – 9/2025, trezor 2020–2022.
6E a ES ostávajú podľa schváleného §1 (A navrhoval obrátiť 6E a ES trezor 2010–14 — neprijaté, kratšie ladenie a staré roky ES už videla rodina).

## Kolo 16 — C: finálna kontrola (A, B aj koordinátor)
- **V2 nie je pripravená na podpis: 10 zásadných chýb.**
  - Z1: ✅ na MGC/6E sa nedá (8c chce SI/6B, ktoré nemáme).
  - Z2: trezory MNQ/MYM/BTC/6E = referenčné okná predvoleného ladenia, k je dnes ≫ 50.
  - Z3: `checkup` otvára trezory.
  - Z4: legacy cez C je mŕtva (DSR).
  - Z5: rozpočet 300 zabíja hypotézy zo štúdií.
  - Z6: ukážka SPRÁVY MGC 2010–21 stojí na zakázaných dátach.
  - Z7: koordinátor zamietol ES trezor 2010–14 s nepravdivým dôvodom.
  - Z8: na Server3 bežia ❌ inštancie.
  - Z9: ranné `--apply` 28. 11. prepíše webapp podľa OOS.
  - Z10: kód pre V2 neexistuje.
- Štatistika kola 14/15 sedí; t = min(obchody, mesiace) stojí len 3–5 p. b. sily.
- Verdikt: A najlepší, B solídne výpočty, ale trezory na ladených oknách; koordinátor prepustil rozpory a B pripísal dohodu z kola 13, ktorú B neurobil.

**Používateľ (27. 11.):** „opravte“. Koordinátor zapracoval Z1–Z10 a menšie nedostatky z kola 16.
- ES trezor 2010–14 (odporúčanie prijaté).
- MGC a 6E majú bez SI/6B najviac 🟡; BTC má 8c na ETH perp.
- Počiatočné k je predvolene prísne.
- `checkup` len na L; legacy a štúdie majú DSR len ako informáciu.
- Príklad SPRÁV je prepísaný; náklad MNQ/MYM 1,75 ticku; α je opravené.
- Ranné nahrávanie 28. 11. je zablokované (`.last_morning`).
Server3 sa nemenil (rozhoduje používateľ).

## Kolo 17 — C: kontrola opráv
- Z1–Z3 a Z6–Z10 opravené; Z4/Z5 len čiastočne (PBO a haircut ostali bránami pre legacy).
- Ďalej: krok 10 počítal na 5 oknách (trezory), SPRÁVY ❌ stálo na vyvrátených dôvodoch, t_req pri k ≈ 160 je 3,6, nie 3,3.
- ES split je v poriadku (L smie obsahovať štúdie). Odhadom je k ≈ 10, takže stačí PF ≳ 1,3.
- **Koordinátor opravil všetko:**
  - krok 10 na L bez roka A;
  - DSR/PBO/haircut pri legacy len informácia;
  - SPRÁVY ⚠ legacy s negatívnym signálom;
  - t_req do k = 160;
  - jedna definícia k (štúdia = 1 na trezor);
  - kalendárne roky;
  - 8c len na L príbuzného trhu;
  - T4b ⏳ pásmo;
  - P3 s SPRÁVY p3;
  - §10 súčet a poradie.

## Kolo 18 — C: podpis
- Všetky body zo 17_C opravené. Pred podpisom ostali tri rozpory: SPRÁVY ❌ v §1, t_req 3,3 v hlavičke a T4 na trezore 6E. Koordinátor ich opravil spolu s drobnosťami (T6 ako výslovná výnimka, k „najviac ~160“, dátumy).
- **Stav: pripravená na podpis používateľom** (C: po týchto troch riadkoch áno).

## Kolá 19–21 — CFD fill model (B → A → C)
- **B (merania zo zrkadla):** graf brokera je bid; spread US100 ~1,4–1,5 b. Nákupná strana sa spúšťa až o spread neskôr. Sklz SL US100 ~1 b, zlata ~0,2 $. Spread sa nezapisuje a vzorky sú malé.
- **A:** spread brať konzervatívne (US100 2,0 b), duplikáty Demo/Server3 nafukujú n. 4 nevyplnené limity „stoja výhry“, 3h posun je fatálny, stratégie na US500 so SL 10–15 b zjedia edge, MNQ +2 ticky.
- **C:**
  - Limity nestáli výhry (cena prešla aj cez SL); 3h posun je už v EA opravený.
  - p75 A čítal zle (2,0 b je voľba, nie meranie); MNQ +2 je len voľba.
  - Prehliadnuté: spread sa dá zmerať hneď z histórie ticku FTMO; limit za trhom sa v MT5 neplní; fill v2 nie je naprogramovaný ani pre futures; krok 12 musí porovnávať medián s mediánom.
  - **Verdikt: zapísať, s podmienkami.**
- **Zapísané do V2 §3** (tabuľka CFD, podmienky, MNQ/MYM +2 ticky, krok 12 medián).

**Používateľ (27. 11.):** „PBO, haircut, DSR nech vidíme aj tieto čísla, nie len PF a WR“. Zapísané do §5: stĺpce v každej tabuľke výsledkov.

**Používateľ (27. 11.), zmeny zapísané:**
- Trezor ≥ 2 roky alebo 30 % použiteľných dát (platí dlhšie; všetky trhy spĺňajú).
- Vo výsledkoch sa ukazuje aj výsledok na iných trhoch.
- Kroky „Demo“ a „Ostrá prevádzka a vypínanie“ sú zrušené, stráži ich používateľ.
- Stop účtu je len denný −4 % (celkový sa nedáva).
- WR 70–100 % je zrušené.
- Prísne počiatočné k platí.
- Posledný rok sa ukazuje len ako kontrola.

**Používateľ (27. 11.): SMERNICA V2 SCHVÁLENÁ A PODPÍSANÁ.**
- Server3 a SPRÁVY vyriešil sám.
- Nové dáta sa nesťahujú.
- Market/limit a IBS + pin bar sa vyberajú vopred a nepočítajú sa do 5 parametrov.
