# 16 — Kontrolór C: nezávislá kontrola SMERNICA_V2 a práce A, B a koordinátora (27. 11. 2026)

*Len čítanie. Overené v `data/archive/tester/` (prvá a posledná sviečka po rokoch), `data_kvalita.json`, `data_noc_roly.json`,
`obchody_sila.py`, v kóde (`tester/`, `tradebot/`, `.nightsearch/`), v `tester/live/mirror.sqlite` a v iCloude (SP500-ES,
EUR-PRIESKUM, ZLATO-PRIESKUM, BTC-PRIESKUM, KLZAKY-STUDIA, OOS-STARE-ROKY, SPRAVY). Skripty: scratchpad `span.py`, `tmin.py`,
`req.py`, `mgc.py`. Riadky smernice = `SMERNICA_V2.md:N`.*

## Zásadné chyby

**Z1. Na MGC a 6E je ✅ nedosiahnuteľné, smernica pritom tvrdí opak.** Krok 8c (`:284–285`) má povinný negatívny test na
príbuznom trhu. Pre MGC je ním SI, pre 6E 6B. Ani jeden v archíve nie je, takže výsledok je ⏳, „nie preskočenie“ (aj ⛔ `:14`).
Napriek tomu `:16` a `:95` píšu, že 6E je „✅ bez kompromisu“ a má „plnú silu dôkazu“, a `:99` a `:438` tvrdia, že MGC „✅ prejde“.
Pre BTC 8c príbuzný trh vôbec nedefinuje, hoci ETH perp v archíve je (`binance/futures/ETH_USDT_USDT-1m-*`). **Oprava:** buď
napísať otvorene „MGC a 6E najviac 🟡, kým sa nestiahne SI / 6B“, alebo pri chýbajúcom príbuznom trhu povoliť ✅ bez 8c
s t_req + 0,3. Pre BTC doplniť ETH perp.

**Z2. Trezory MNQ, MYM, BTC a 6E ležia v období, na ktorom sa ladilo všetko.** Trezor 2022-10-01 – 2025-09-03 (`:96–98`)
sú presne tri z piatich `REFERENCE_WINDOWS` (`tester/hyperopt.py:56–58`). Na nich beží predvolené ladenie
(`glsearch` 2021-10 – 2025-09, `12_B:17`) aj ~1,8 mil. pokusov. Trezor 6E 10/2021 – 9/2025 sú štyri z tých piatich okien
a k tomu OOS EUR kópií (`SMERNICA_EUR.md:15–16`). Krok 8b definuje k ako „hypotézy, ktoré sa **kedy** pozreli na trezor“ (`:270`).
Pri doslovnom čítaní je dnes na MNQ k ≫ 50 (v `tradebot/strategies` je ~160 kľúčov), teda t_req ≥ 3,3. Pri 210 obchodoch to
vyžaduje pozorovaný PF ≥ 1,59 a pri skutočnom PF 1,5 vyjde sila 37 % (`req.py`). Ak sa naopak k počíta až od V2, trezor je
čistý len na papieri. `vaults.json` neexistuje a smernica nepovie, akým k začína. **Oprava:** zapísať počiatočné k pre
každý trezor z histórie (legacy rodiny, ktoré bežali na danom období, plus štúdie). Číslo „PF ≳ 1,32“ v `:96`, `:279` a `:438`
nahradiť hodnotou pre skutočné počiatočné k.

**Z3. `checkup` „zachovaný bez zmeny“ otvára trezory pri každej stratégii.** `:33` a `:431` checkup zachovávajú a krok 7 ho
používa na break-even (`:247`). `tester/checkup.py:46` však počíta na `REFERENCE_WINDOWS` 2021-10 – 2026-09, teda na celom
trezore MNQ, MYM, BTC a 6E a na časti trezoru MGC (10/2021 – 12/2022). CLAUDE.md navyše žiada checkup pri každej novej stratégii
(„hotová až so základnou analytikou“). §10 (`:460`) z checkupu vyraďuje len rok A. **Oprava:** checkup v V2 púšťať len na L
(prípadne WF OOS). Trezor smie počítať jedine príkaz `--vault`. Zmenu zapísať aj do CLAUDE.md.

**Z4. Legacy cesta cez C je mŕtva vo vlastnom znení smernice.** Krok 10.1 (`:298`) vyžaduje krok 7, teda DSR ≥ 0,95 pri N_eff
a ≥ 0,50 pri surovom N, a „neprejde DSR → ❌“ (`:251`). Podľa B dnes 0,95 nesplní žiadna stratégia (najvyššia 0,93, TKS 0,79,
NOA 0,33; `02_B:68`, `:90`), a to ešte pri N oveľa menšom, ako aké predpisuje V2 (tisíce až 82 000). Tabuľka stavov (`:420`, `:426`)
však legacy dáva „⚠, krok 10, najviac 🟡, dôkaz z C“. **Oprava:** pri legacy brať DSR len ako informáciu a nechať rozhodnúť
C, alebo napísať, že legacy = ❌ a C beží len ako výskum exekúcie.

**Z5. Rozpočet 300 zabíja každú hypotézu zo štúdie, smernica jej pritom sľubuje 🟡.** §2 (`:161–162`) počíta do rozpočtu
aj behy štúdií, „vyčerpaný = koniec“. KLZAKY-STUDIA má ~500 000 nastavení (`STUDIA.md`), z nej vzišla MTK EMAS. V §1 (`:89`) a v §7
(`:425`) majú takéto hypotézy „najviac 🟡 / ⏳ C“. **Oprava:** určiť, koľko sa za štúdiu odpočíta (napr. N = počet pravidiel
vybraných zo štúdie, nie počet behov štúdie), alebo priznať, že hypotézy zo štúdií sú ❌.

**Z6. Ukážkový „trezor B v praxi“ (SPRÁVY MGC, `:144–148`, `:416`) stojí na dátach, ktoré §1 sám zakazuje.** Ide o rovnaký
typ chyby, ako bolo NQ/YM/GC. MGC 2010–2019 má pokrytie jadra 8–39 % (2016–18 64–77 %, `data_kvalita.json`) a §1 ho vylučuje
(`:126`). Čisté sú z toho len okná 2019/20 a 2020/21 so 107–143 obchodmi, čo je pod 150 → podľa 8b ⏳, nie ❌. Kalendár ForexFactory
má na ISM zhodu ~90 % (`07:5`), hoci §1 (`:141–142`) žiada ≥ 95 % na každý typ. Okrem toho behy 1/2020 – 9/2021 otvorili nový
trezor MGC 2020–22. **Oprava:** SPRÁVY legacy dať ❌ z dôvodov, ktoré obstoja: > 5 parametrov, DSR a strata v okne 2020/21.
Príklad prepísať a do k trezoru MGC pripočítať SPRÁVY aj 11 MGC rodín z triedenia (`PRAVIDLA_TRIEDENIA.md:4`: MGC 1/2020 – 9/2021).

**Z7. Zamietnutie ES trezoru 2010–14 koordinátorom bolo zdôvodnené nepravdivo.** `VYCUC.md:179` uvádza „kratšie ladenie
a staré roky ES už videla rodina“. Pri ES však A navrhol ladenie **dlhšie**: 10,7 roka (2015-01 – 2025-09) proti 7,3 roka vo V2 (`13_A:44–45`).
Triedenie bežalo na ES 7/2010 – 9/2021 (`PRAVIDLA_TRIEDENIA.md:4`), teda zasiahlo obe obdobia rovnako. Trezor V2 10/2017 – 9/2021
leží v kontrole SP500-ES (US500 2015–2020, `SP500-ES/PRECITAJ_MA.md:50`, `:61`, `:85`) aj v KLZAKY (ES od 2016). ES je pritom jediný trh,
kde je ✅ reálne (Z1, Z2). Okrem toho V2 na ES nechá 2021-10 – 2025-09 (3,9 roka) **bez úlohy**: nie je to L, B ani A (`:94`).
Pri 6E je zamietnutie obhájiteľné (L by sa skrátilo z 5,75 na 3,9 roka, EUR kópie videli obe polovice), ale trezor V2 je pre
hypotézy z EUR-PRIESKUM (charakter 2021–2026) spálený. **Oprava:** ES vrátiť používateľovi na rozhodnutie s pravdivým porovnaním
a určiť, na čo slúži ES 2021–25 (napr. 8c pre MNQ a MYM).

**Z8. Živé riziko trvá.** Podľa `mirror.sqlite` (last_seen 27. 11., ~09:07 UTC) beží na `531513073-FTMO-Server3`
`spravynet profil_3` (XAUUSD, posledný fill 25. 11.), `tksnet TKS_1` (fill 26. 11.), `ibsentrynet IBS_EZ_11` a `noanet NOA_1`. Podľa V2 sú
prvé tri ❌ a NOA ⚠. Stop účtu v EA (krok 14) neexistuje a NFP je 4. 12. Toto rozhoduje používateľ, ale smernica pri nich stav
nemá ako „beží naživo proti V2“.

**Z9. Ranné nahrávanie zajtra prepíše webapp podľa OOS napriek pauze.** `glmorning.sh` nastaví TESTS=1, keď je stavový
súbor novší ako `.last_morning`. `hub_state.json` má 27. 11. 09:48, `.last_morning` 07:29, takže 28. 11. o 6:00 pobeží
`glsmernice --apply` aj `glwebvyber --apply` (`glmorning.sh:14`, `:29–30`) a výsledok sa pushne. P6 nie je vykonané. **Oprava
(rozhoduje používateľ):** vypnúť krok `--apply` alebo `sk.tradebot.morning`.

**Z10. V2 sa s dnešným kódom zaviesť nedá. Mimo §10 navyše chýba:** `--fill`/fill v2, `register/`, `vaults.json`,
`tester/walkforward.py` a `tester/pbo.py` neexistujú (grep). `skipRoll` je len v `nocpon` a vo všetkých profiloch je `false`,
hoci V2 ho chce „predvolene zapnutý pre každú stratégiu“ (`:137`). `rolls.json` obsahuje dátum a kontrakt, nie skok (`:134`).
§10 nemá položky pre ratio back-adjust indikátorov v Pythone aj C# (s paritou), pre počiatočné k (Z2), pre meranie „iného režimu“
ani pre kontrolu kalendára. Odhad 5–7 týždňov je preto nízky.

## Menšie nedostatky
- **t_req (`:271`):** veta „jednostranný, α = 0,05“ je nesprávna. Tabuľka 2,0/2,6/2,8/3,0/3,3 je Bonferroni pri jednostrannom
  α = 0,025, pri jednostrannom α 0,05 by vyšlo 1,64/2,33/2,58/2,81/3,09. A to napísal správne (`15_A:19`), koordinátor to zapísal zle.
- **Dve definície k:** pre rodinu platí „≥ 6 kópií → k ≥ 5“, pre trezor kumulatívne cez `vaults.json` (`:267`, `:270`). Ako sa
  skladajú (súčet alebo maximum), smernica nehovorí. „≥ 6 kópií → k ≥ 5“ nie je Bonferroni (to by bolo k = 6).
- **Počítanie obchodov:** „≥ 150 na trh“ a zároveň „trhy s ρ > 0,5 sa nesčítavajú“ (`:216–217`, `:261`) si odporujú. Ak je n za trh,
  nesčítava sa nič. Netreba ani ρ medzi MNQ a ES, ktorých trezory ležia v rôznych rokoch.
- **WF 24/6 v kroku 6 (`:228`) proti 18/6 v §1:** na MGC (32 mesiacov) zostanú 2 kúsky, takže „≥ 75 % v pluse“ = oba.
  Čiastočné roky L (ES 2010 7 mesiacov, MGC 2025 8 mesiacov) nemajú pravidlo pre „≥ 75 v každom roku“.
- **„Iný režim“:** 8b hovorí o roku (`:258`), §1 o štvrťroku s ATR mimo IQR (`:113`).
- **Zvyšky B′:** ⛔ `:13`, §6 `--vault B'|C`, 8b „B alebo B′“ a krok 10 odkazujú na trezor 6E B′ 2010–15. Ten v §1 už nie je, takže čistenie
  6E (`:127–131`) nemá v smernici účel.
- **T4 (`:405`):** obdobie 10/2021 – 9/2026 nazýva „rok A pre 6E“, hoci 10/2021 – 9/2025 je trezor 6E. Beh tak zvýši k trezoru.
- **Tabuľka štúdií (`:82–87`):** BTC-PRIESKUM nepoužil len Dukascopy. Bral aj Binance perp 2019-09 – 2026-09 (`PRECITAJ_MA.md:3`, `:24–25`),
  teda trezor BTC videl. ZLATO-PRIESKUM videl MGC 2011–2025, nie 2020–9/2026. KLZAKY začína ES a MGC od 2016.
- **Pripisovanie:** `:73` a `:75` píšu „dohoda A + B, 27. 11.“, ale B na `13_A` nikdy neodpovedal (KONVERZACIA nemá kolo B po 13).
  Obrátenie MGC je návrh A a koordinátora. B v `12_B` navrhol opak (G1).
- **Z dohody 14_B/15_A vypadlo:** „bez MC → najviac 🟡“, „t_mesiace ≥ 24 mesiacov / HAC“ a „MC n = obchody za rok × 2“.
- **Detektor rolovania** (`dq_night_rolls.py:23–26`) hlási „tam a späť“ pri každom rolovaní ES, 6E a MGC od 2020 (27/27/34 záznamov),
  lebo jednociferný rok v kóde kontraktu sa po 10 rokoch opakuje. Záver „len MGC 1/2011“ (`:140`) je správny, ale JSON ho nepodporuje.
  Ako automatická kontrola by to nefungovalo.
- **Náklad MNQ a MYM 1,5 ticku** je pod tým, čo agenti sami namerali (~1,7–1,8 ticku; `03_B`, `04_A`).
- **P5 nie je splnené:** `git status` ukazuje necommitnuté zmeny `PRESIEL_SMERNICAMI_*` profilov (fibomgcnet, nyvaesnet, ibsentryesnet).

## Čo je v poriadku
- Dátumy v §1 sedia so súbormi: ES 2010-06-06, MNQ 2019-05-05, MYM 2019-06-02, BTC 2019-09-08, 6E 2016-01-03, MGC 2020+.
  Koniec archívu: ES 19. 10., MNQ a MYM 9. 11., 6E 28. 9., MGC 16. 9., BTC 4. 9. Pokrytie a nočné okná sedia s JSON (MYM noc 2019 86,5 %, 2024 94,8 %).
- Obrátenie MGC je z hľadiska režimu správne: trezor 2020–22 má max DD −21,6 % (vrchol 6. 8. 2020), L 2023 – 9/2025 rastie o +97 % pri DD −10,9 % (`mgc.py`).
- Výpočty v `obchody_sila.py` sú správne (sila, n pre 80 %, PF z t_req). Pravidlo t = min(t obchodov, t mesiacov) stojí pri iid
  len ~3–5 p. b. sily, falošný poplach nezvyšuje (pri 35 mesiacoch 1,8–1,9 % pri t 2,0; `tmin.py`), a to je rozumná cena. Mesačné t pri
  35 bodoch kryje zhluky nad 1 mesiac, nie kratšie. Zrušenie pevných 300 je odôvodnené.
- Jedno rozdelenie na trh, trezor mimo štúdií, stop účtu lokálne v EA a „✅ len skriptom, podpis používateľa“ sú správne.

## Verdikt
- **A (Prokurátor):** najlepšia práca v debate. Odhalil štúdie, kópie, šikmosť a prekliatie víťaza a správne opravil Bonferroniho.
  Slabiny: v `13_A` neoveril obdobie BTC-PRIESKUM („nedokázal priradiť“) a nevidel, že checkup a referenčné okná otvárajú trezory (Z2, Z3).
- **B (Inžinier):** výpočty a merania sú solídne a priznal, kde sa A mýlil. Slabiny: navrhol trezory MNQ, MYM a BTC presne na oknách
  predvoleného ladenia a „✅ je možné“ ponúkol bez počiatočného k. Na `13_A` neodpovedal a s 8c vedome nechal 6E a MGC bez ✅.
- **Koordinátor:** zapísal dohody väčšinou verne, ale (1) prepustil Z1, Z4 a Z5, teda rozpory medzi krokmi, ktoré si všimne každý,
  kto smernicu číta celú, (2) ES zamietol s nepravdivým dôvodom (Z7), (3) ako ukážku dal MGC 2010–21, teda tú istú triedu chyby
  ako NQ/YM/GC (Z6), (4) pripísal B dohodu, ktorú B neurobil, a zle zapísal α. Smernica v dnešnom znení nie je pripravená na podpis.

## Na rozhodnutie používateľa
1. Server3: spravynet profil_3, TKS_1 a IBS_EZ_11 sú podľa V2 ❌ a bežia, NOA_1 je ⚠. Do NFP 4. 12. vypnúť alebo vedome nechať (Z8).
2. Zastaviť zajtrajšie `--apply` v rannom nahrávaní (Z9).
3. ES trezor: V2 (10/2017 – 9/2021, spálený štúdiami S&P) alebo 2010-06 – 2014-12 s ladením 2015 – 9/2025 (Z7).
4. MGC a 6E: stiahnuť SI a 6B, alebo prijať „najviac 🟡“ (Z1).
5. Či sa počiatočné k trezoru ráta z celej histórie (prísne, ✅ takmer nedosiahnuteľné), alebo až od V2 (Z2).
6. Rozpor s vašimi pravidlami, ktorý V2 nespomína: povinné „market/limit + IBS + pin bar“ zaberie 2 z 5 voľných parametrov
   a „vždy aj posledný rok“ (tabuľky) sa bije s §5 (bez „posl. rok PF“).
