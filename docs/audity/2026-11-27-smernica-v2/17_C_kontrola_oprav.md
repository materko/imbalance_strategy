# 17 — Kontrolór C: kontrola opráv SMERNICA_V2 po `16_C` (27. 11. 2026)

*Len čítanie. Porovnané s `SMERNICA_V2.bak3.md` (diff), riadky = `SMERNICA_V2.md:N`. Rozhodnutia používateľa: ES trezor 2010–14,
prísne počiatočné k, MGC a 6E najviac 🟡.*

## Opravené
- **Z1** `:15`, `:17`, `:99`, `:103`, `:299–300`: MGC a 6E najviac 🟡, BTC ↔ ETH perp doplnené. **Z2** `:105–107`, `:100`, `:102`, `:294`, §9.6.
- **Z3** `:14`, `:35`, `:259`, `:397`, `:447`, `:482`: checkup len na L. **Z6** `:152–157`: už nie je príklad trezoru, dôvody sú prepísané.
- **Z7** `:98`, `:115`, `:454`: ES trezor 2010–14. ES 2021–25 má teraz úlohu (je v L). **Z8** `:432`, `:457`. **Z9** `:412`. **Z10** `:483–485`, `:492`.
- Menšie: α `:286`, jedno k `:280–281`, obchody na trh `:228`, `:273`, WF 18/6 `:240`, `:245`, iný režim `:270`, B′ preč, T4 `:420`,
  štúdie `:87–91`, pripisovanie `:75`, `:77`, `:103`, MC/HAC `:279`, `:284`, detektor `:147–148`, náklad 1,75 `:194`, P5 `:411`.
- **ES L 2015–2025 s referenčnými oknami a štúdiami je v poriadku.** L je obdobie, ktoré sa smie vidieť, a podmienka platí len pre trezor.
  ES 2010–14 videlo len triedenie (ORB 15/5, NY VA, IBS EZ ES, IVB, Williams R, MTK EMAS ES; ~10 profilov). Počiatočné k je teda ~10,
  t_req ~2,8 a pri ~460 obchodoch stačí PF ≳ 1,3. Tvrdenie „✅ reálne len na ES“ obstojí.

## Zle alebo chýba
**Blokujúce (rozpory medzi krokmi):**
1. `:313` krok 10.1 „PF ≥ 1,15 na 5 oknách“: piate okno 20250904–20260904 je rok A (`:73`, `:384`). Okná 2022–25 sú trezory MNQ, MYM a BTC,
   2021–25 trezor 6E a 10/2021–12/2022 časť trezoru MGC. Bije sa to s `:222` (krok 3 na L), `:35` a `:397` (len L). Cez `:314` tou istou
   cestou idú aj **nové** hypotézy zo štúdií, takže tie otvoria trezory s plnou váhou k. Oprava: krok 3 aj pri legacy na L trhu, bez roka A.
2. Z4 a Z5 sú opravené len čiastočne. `:263` vyníma iba DSR. Haircut (`:258`, N = N_eff ≥ N/50, teda pri 82 000 alebo 500 000 behoch
   tisíce) a PBO (`:257` chce mesačný PnL všetkých konfigurácií, legacy ho v registri nemá) ostávajú bránami → legacy aj štúdie skončia ❌.
   Oprava: pri kroku 10 brať DSR, PBO aj haircut ako informáciu a rozhodnutie nechať na C. Haircut ponechať len na veľkosť.
3. `:431` SPRÁVY ❌ sa opiera o „DSR neprejde“, hoci `:263` to robí len informáciou. Ďalší dôvod, „strata v okne 2020/21“, má 107–143 obchodov,
   čo je podľa `:154` a `:274` len ⏳. Pravidlo „> 5 parametrov“ pre legacy nikde neplatí (`:181–184`, krok 10).
   Treba napísať pravidlo, podľa ktorého sú ❌ (napr. legacy > 5 parametrov → ❌), alebo im dať ⚠ / ⏳.
   `:455` (§9.2) stále píše „❌ (trezor B)“, čo je zvyšok Z6.

**Menšie:**
4. `:432` dáva IBS_EZ_11 (ibsentrynet = MNQ) ❌, ale `:439` má „IBS EZ MNQ/MYM ⚠ do T1“. Chýba dôvod: ladenie na živom období podľa `:56`.
   `:408` (P3) nemá SPRÁVY profil 3, hoci `:457` ho má.
5. `:100`, `:107`, `:463`: pri k ≫ 50 platí t_req 3,3 len ako dolná hranica. Tabuľka `:288–290` končí pri k = 50.
   Pri k ≈ 160 (počet kľúčov) je t_req ≈ 3,6 a pri 210 obchodoch to znamená PF ≳ 1,65. Doplniť stĺpce k 100 / 200 (3,5 / 3,7).
6. `:285` znovu definuje k ako „počet hypotéz“ bez kópií, kým `:280` kópie zahŕňa. Jednu z definícií zrušiť.
   `:106` nehovorí, či sa štúdia s 500 000 nastaveniami počíta ako 1.
7. `:229`: v zátvorke „ES 2015 nie“ chýba, že aj ES 2025 (do 3. 9.) je neúplný rok. Neúplné sú aj roky na okrajoch L
   pri MNQ, MYM, BTC a 6E (2019, 2021, 2022). Pravidlo treba napísať všeobecne a určiť, či „rok“ znamená kalendárny rok, alebo okno 10–9.
8. `:98` vs `:120`: iný režim ES trezoru nie je zmeraný. Kritérium poklesu nevyjde, lebo L má covid (−35 %) aj rok 2022 (−25 %).
   Ostáva ATR (2011). Treba ho zmerať a zapísať, inak podľa `:271` platí najviac ⏳.
9. `:299` 8c neurčuje obdobie na príbuznom trhu. Pre MNQ a MYM je prirodzené ES 2022–25 (to je L ES). Pre ES hypotézu by MNQ 2022–25
   otvorilo trezor MNQ (+k). Treba to napísať.
10. `:421` T4b nemá výsledok pre PF 1,00–1,03. Pri prechode dá ⚠, teda ten istý stav ako dnes (`:438`), takže test vie len zamietnuť. Treba to povedať.
11. `:115` schéma ES pre NQ/YM/GC: GC 2011–14 videl ZLATO-PRIESKUM (`:87`) a NQ článok NOA (SPY 2007–24). Treba doplniť „+ počiatočné k“.
12. §10 `:490`: riadok CLAUDE.md nemá zmenu „checkup len na L“ (Z3). Poradie `:493–499` nemá nové riadky (počiatočné k,
    checkup na L, back-adjust). Počiatočné k musí byť hotové pred T4, ktorý k trezoru 6E zvyšuje. Súčet tabuľky je ~28–34 dní,
    čo je ~6–7 týždňov, nie 7–9. Ako rezerva to obstojí, len to treba napísať.
13. `:412` P6: blok platí len dovtedy, kým `hub_state.json` (9:48) ani iný stav nie je novší než `.last_morning` (27. 11. 10:17).
    Ktorýkoľvek beh hubu dnes ho zruší a 28. 11. o 6:00 znovu pobeží `--apply`. `:7` má stále „stav 26. 11.“

## Verdikt
**Pripravená na podpis: nie, zatiaľ nie.** Z1–Z3 a Z6–Z10 sú opravené vecne správne. Zostávajú tri rozpory medzi krokmi (body 1–3):
krok 10 na 5 oknách otvára trezory a rok A, haircut a PBO stále zabíjajú legacy aj štúdie a dôvod ❌ pri SPRÁVACH je v rozpore s vlastným textom.
Po ich oprave a jednom prechode bodov 4–13, ktorý trvá zhruba hodinu práce bez nových meraní, áno.
