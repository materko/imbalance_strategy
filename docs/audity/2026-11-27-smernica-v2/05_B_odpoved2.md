# Agent B (Inžinier) — 3. kolo: odpoveď na repliku

*26. 11. 2026, len čítanie. V tomto kole som nové veci overil v `glsearch.py:595–606`, `base_*.json`,
`PRESIEL_SMERNICAMI_IBS_EZ_ES_1.json` a `gl_state.json`.*

Pán Prokurátor, prijímam D1–D5, N1, výpočtový odhad aj vaše čísla k fill modelu. Všetko ide do SMERNICA_V2. Pri
N2 s vami súhlasím čiastočne. V jednom bode sa mýlite vy a v dvoch sme sa obaja nechali oklamať tým istým triedením.

## 1. Kde sa mýlite: IBS EZ ES nemá bodové prahy
`tradebot/strategies/ibsentryesnet/configs/PRESIEL_SMERNICAMI_IBS_EZ_ES_1.json` má **všetky** prahy v ATR
(`fvgMinSize {1,5 atr}`, `minImbSizePoints {0,3 atr}`, `srClusterPoints {1,54 atr}`…). Kópie na ES, MGC a EUR
`glsearch` ladí v ATR (`A = lambda v: {"unit": "atr"}`), MNQ originál v bodoch. Argument B2 preto ES nezasahuje
a **IBS EZ ES 0,75 (3/12) ostáva čistým dôkazom**. Výhradu mám len k nákladu: 1 tick na stranu bol pri ES 1 050–2 000
percentuálne drahší, a „pred poplatkami 1,10“ znamená, že hrubý edge existuje, len ho poplatky zjedia. Pre živé
rozhodnutie je to rovnaké. T1 na MNQ/MYM s prepočítanými prahmi podporujem.

## 2. Kde sme sa mýlili obaja: dva „✅“ zo starých rokov sú in-sample
- **Williams R 6E:** `glsearch.py:595–606` má `PERIODS["wpreur"] = ("20160101-20211001", "20211001-20260904", …)`,
  čiže **ladila sa na 2016–9/2021**. To je presne obdobie „starých rokov“ v OOS-STARE-ROKY. Zhoda „1,54 vs 1,53
  z ladenia“ je preto tautológia. Moje t ≈ 4,1 neplatí a beriem ho späť. **Skutočné OOS má 6E na 10/2021–9/2026.**
  Tam 9 z 9 kandidátov skončilo nad 1,0: medián 1,16, rozsah 1,03–1,33 a 460–1 430 obchodov. To je lepší obraz než
  pri MNQ stratégiách (chvost z mediánu 1,0), ale náklad je v percentách (~0,4 ticku namiesto ~1). **Váš T4 preto
  treba spustiť na 10/2021–9/2026, nie na 2016–2021.**
- **Noc + pondelok:** `base_nocpon.json` píše „z prieskumu Nasdaqu: MNQ 2019–2026“. Prieskum teda roky 2019–21
  videl a ✅ je in-sample ako pri MTK ORB. Z kandidáta ho preraďujem na **⏳ neoverený**. Čisté dáta preň budú
  až NQ 2010–2019.

Záver k (b) je teda ešte tvrdší: **zo zoznamu ✅ po tomto kole nezostal ani jeden čistý dôkaz zo starých rokov.**
Najlepšie podložené je 6E na 2021–2026, čo je reálne OOS, ale na jedinom trhu po prežití z piatich (D1). Hneď za
ním ide NOA ako hypotéza.

## 3. NOA: dohoda a nový test
Prijímam „pozastavený podozrivý“ pre **ladené** profily (37 700+ pokusov, DSR 0,33). Treba však dodať fakt:
`base_noa.json` je „presne podľa článku Zarattini, Aziz, Barbon (2024), Beat the Market“. Je to vonkajšia,
publikovaná hypotéza (SPY 2007–2024) **s nulovým hľadaním na našich dátach**. Navrhujem preto **T6: NOA podľa článku
bez zmeny parametrov na NQ 2010–2019**, s tickovým nákladom a fill-through. Hranica: PF ≥ 1,10, t ≥ 2,0, ≥ 60 %
rokov v pluse. Je to jediný test v repe s N = 1. Pozor na McLean–Pontiff: publikovaný edge po publikácii slabne.

## 4. Ostatné body
- **D3 (N_eff):** prijímam ρ > 0,5, podlahu N/50 aj dvojitú bránu (DSR pri N_eff aj pri surovom N). Do smernice
  idú zmrazené.
- **D4:** súhlasím. Obdobie 9/2026–11/2026 slúži len na kontrolu exekúcie, čistý trezor C začína 1. 12. 2026.
- **N2:** pozitívny dôkaz má len iné pásmo alebo iná trieda aktív, súhlas. Nesúhlasím však s tým, aby sa ES a YM
  vyhodili. Ako **negatívny test** majú veľkú silu: stratégia, ktorá na ES bez zmeny prehráva, je podozrivá
  (Williams R ES 0,67). V smernici sú preto „povinne nesmie zlyhať“, nie „počíta sa ako potvrdenie“.
- **ORB 15/5 ES:** ustupujem. Rozhodne T4b s vašou hranicou.
- **Trezor B je už sčasti spálený.** Triedenie 26. 11. sa na ES 2010–21, MGC 2020–21, MNQ/MYM/BTC 2019–21 a 6E
  2016–21 už pozrelo. Pre stratégie z `webapp_vyber.json` je to použitý trezor. Čisté sú len **NQ 2010–2019,
  YM 2010–2019, GC 2010–2019** (treba ich stiahnuť), DAX a Nikkei a od 1. 12. 2026 trezor C.
- **SPRÁVY a pravidlá FTMO:** podľa používateľa náš účet smie obchodovať správy, takže argument o NFP v T+0 a
  2-min pravidle (môj A9, váš bod 4) **sťahujeme**. Ostáva len preladenie: ~40–50 parametrov na ~36 obchodov za rok,
  staré roky neoverené a kalendár až od 2021. Do V2 ide všeobecný krok „overiť pravidlá konkrétneho účtu“ bez
  predpokladov.
- **SPRÁVY ako hypotéza:** uznávam, že sú postavené na správaní trhu, nie na hrubom hľadaní. DSR 0,959 je jediný nad
  0,95. Vo V2 ich vedieme ako **⏳ kandidáta s ekonomickým dôvodom** a chýba im len trezor B. Výskum však videl aj
  rok A (2 302 kombinácií × 5 okien, 3 seedy, 125 RRR) a to sa do N počíta. V2 všeobecne zvýhodňuje ekonomický dôvod:
  t_req −0,3 a haircut z ½ N_eff.
