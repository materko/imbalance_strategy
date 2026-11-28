# Register pokusov, trezory a zámky (SMERNICA V2 §1–2, kroky 6 a 8)

*Zavedené 28. 11. 2026 podľa zadania U6 a U7 ([ZADANIE_IT.md](audity/2026-11-27-smernica-v2/ZADANIE_IT.md)).
Kód je v [tester/register.py](../tester/register.py), dáta v `tester/register/` (v gite).*

DSR, haircut aj prah t na trezore závisia od toho, koľko sa toho skúšalo. Register to počíta sám a nedovolí
pustiť hľadanie na obdobie, ktoré má ostať na kontrolu.

## Čo leží v `tester/register/`

| súbor | čo | kedy |
|---|---|---|
| `<hypotéza>.md` | hlavička: dôvod edge, zdroj, štúdie, mriežka, trhy, L, hranice brán, typ vstupu, pevné parametre, výnimka, iný režim | commit **pred prvým behom**; zmena po ňom = nová hypotéza |
| `<hypotéza>.jsonl` | pokusy, len pridávanie: čas, kľúč, trh, TF, parametre, obdobie, zdroj, git hash kódu stratégie, PF, obchody, mesačný PnL | každý pokus |
| `vaults.json` | trezory na trh: L, B, A, `c_from`, počiatočné k s rozpisom, kto trezor otvoril, zámok walk-forwardu | k0 commit **pred prvým otvorením** |

## Pravidlá v kóde

| pravidlo | kde sa vynúti |
|---|---|
| hľadanie len na L trhu (nie trezor B, rok A ani C) | `check_search`: `native_hyperopt`, `cli hyperopt`, `cli sweep`, `cli matrix` (iný trh len na jeho L), webapp hyperopt, `cli run --hypothesis` |
| `checkup` a hyperopt bez prepínača počítajú na **L po rokoch** (`l_windows`), nie na piatich referenčných oknách | `hyperopt.windows_for`; pre trh mimo §1 (CFD, akcie, ETH) ostávajú referenčné okná |
| hlavička hotová a commitnutá | `require_header` pri každom pokuse a otvorení trezoru |
| ≤ 300 konfigurácií na hypotézu (všetky kópie a trhy, aj plató; WF, štúdia a legacy sa nerátajú) | `append` |
| ≤ 5 voľných parametrov vrátane TF (bez `## Pevné parametre` z hlavičky) | `append` |
| ≤ 10 nových hypotéz za štvrťrok na jeden trezor | `append` (prvý pokus hypotézy) |
| trezor raz na hypotézu, len s commitnutým k0 a trhom z hlavičky; dĺžka ≥ 2 roky alebo ≥ 30 % dát (L + B) | `open_vault` |
| walk-forward raz na hypotézu | `lock_wf` |

Konfigurácia = kľúč, trh, TF a parametre. To isté nastavenie na inom okne nie je nový pokus.

**N** pre DSR = konfigurácie v registri bez WF, plus odhad `n` pri legacy a štúdiách.
**N_eff** = zhluky mesačného PnL pri |ρ| > 0,5, podlaha N/50.
**k trezoru** = počiatočné k + každý kľúč (kópia rodiny) každej hypotézy, ktorá ho otvorila.
**t_req** = Φ⁻¹(1 − 0,025/k): −0,3 za ekonomický dôvod, +0,5 pri výnimke pod 75 obchodov za rok, +0,3 pri šikmosti < −1.

## Počiatočné k (28. 11. 2026)

`python -m tester.register k0 --write` prejde históriu behov aj archív (len `settings`, ~1 min) a štúdie §1.
Pravidlo je prísne (§1, §9), teda horný odhad:

- ráta sa každý kľúč, ktorý mal beh v období trezoru;
- trezor, ktorý zasahuje do referenčných okien 10/2021–9/2026, dostane všetky kľúče registra (videli ich všetky legacy rodiny);
- triedenie starých rokov dáva najmenej 11 rodín;
- každá štúdia, ktorá obdobie videla, je +1.

| trh | k0 | t_req | z čoho |
|---|---|---|---|
| ES (2010–14) | 11 | 2,84 | triedenie (v histórii 3 kľúče) |
| 6E | 154 | 3,59 | 153 kľúčov registra + EUR-PRIESKUM |
| MNQ | 164 | 3,61 | 161 kľúčov (aj zrušené ibret) + KLZAKY, NASDAQ-STUDIUM, nocpon |
| MYM | 156 | 3,60 | 155 kľúčov + KLZAKY |
| BTC | 157 | 3,60 | 155 kľúčov + BTC-PRIESKUM, KLZAKY |
| MGC | 159 | 3,60 | 157 kľúčov + KLZAKY, ZLATO-PRIESKUM |

Behy automatu z Mac mini, ktoré sa do histórie nevrátili (`gl_state`, `hyper_state`), tu nie sú. Pri trhoch
v referenčných oknách to nevadí, lebo tie už majú všetky kľúče. Pri ES 2010–14 by mohli k zvýšiť.
Hranica C (`c_from`) sa zapíše ručne (P7: do 30. 11. 2026). Kým tam nie je, trezor C sa neotvorí.

## Príkazy

```
python -m tester.register new orb-pondelok          # šablóna hlavičky -> vyplniť a commitnúť
python -m tester.register check orb-pondelok
python -m tester.register periods MNQ               # L, B, A a okná L po rokoch
python -m tester.webapp.cli run --hypothesis orb-pondelok --profile ZAKLAD_MNQ --strategy orb --timerange 20200101-20210101 --note "…"
python -m tester.register status orb-pondelok       # N, N_eff, rozpočet, voľné parametre, trezory
python -m tester.register legacy ibsentry --keys ibsentry,ibsentrynet,ibsentryneteod --n 20710   # odhad N legacy
python -m tester.robust --hypothesis orb-pondelok …  # DSR s N z registra namiesto ručného --trials
python -m tester.webapp.cli run --hypothesis orb-pondelok --vault B --profile … --strategy orb --keys orb,orbnet --note "trezor"
```

`run --vault` najprv zapíše otvorenie (zámok, k + počet kľúčov) a až potom spustí beh na celom trezore.
Spadnutý beh trezor nevracia, lebo otvorený je už výberom nastavenia.

## Čo ešte nie je

- Automat `.nightsearch` (glsearch, glhyper, glwr, glrr) na Mac mini zapisuje do registra cez `tester.register.append`.
  Napojenie treba spraviť tam (U6). Z repa vidno len snímku jeho kódu v `docs/audity/2026-11-27-smernica-v2/nightsearch_kod/`.
- Meranie „iného režimu“ sa nepočíta. Do hlavičky ho píše človek. Bez neho otvorenie trezoru ohlási, že výsledok je najviac ⏳.
- Trezor 8b (t z obchodov a mesačného PnL s HAC, t_req, 🟡/✅ podľa počtu obchodov), Monte Carlo veľkosti a portfólio
  (krok 11) ešte nie sú v kóde. Brány z kroku 7, walk-forward a stav sú (`tester.overfit`, `tester.walkforward`,
  `tester.robust`).
