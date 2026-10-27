# Prepočet meraní po oprave auditu (N-CORE-1/2/3, N-LIVE-20) — 2026-10-26

Audit architektúry ([AUDIT_architektura_2026-10-25](../audity/AUDIT_architektura_2026-10-25.md)) zmenil
dve veci, ktoré môžu pohnúť číslami starších meraní:

- **N-CORE-1/2/3** (`64fe7cfbc`): Freqtrade dáva market vstup za cenu, ktorú navrhne sám (`proposed_rate`,
  open ďalšej sviečky), nie za close signálnej sviečky. Emulátor MultiCharts priradí SL/TP
  príkazu, ktorý sa naozaj vyplnil, a keď sa limitka vyplní uprostred minúty a cena v tej istej
  minúte prejde aj stop, zavrie obchod stopom hneď. Pred oknom sa prehrá `max(300, required_history)`
  barov predhistórie.
- **N-LIVE-20** (`6f85ae44f`): pri veľkosti z rizika (`maxLossDollar`) platí strop straty vždy.

Prepočítali sa hlavné konfigurácie dokumentov, ktoré tieto zmeny môžu zasiahnuť, na piatich
referenčných oknách. Behy išli cez `cli run` s 1m detailom a sú v histórii s poznámkou
„prepočet po N-CORE-1/2/3, N-LIVE-20: …“. Poplatok je 0,05 % na stranu a peňaženka 10 000,
pokiaľ nie je uvedené inak. Pri zmene, ktorá nebola jasne spôsobená opravou, rozhodol beh
toho istého okna na kóde pred opravou (`64fe7cfbc^`) v dočasnom worktree.

## Záver

_Nechané prázdne na človeka._

## Zhrnutie

| dokument | konfigurácia | zmena |
|---|---|---|
| [OPTIMALIZACIA](OPTIMALIZACIA_2026-09-05.md) §1 | `btcusdt_3m_binance_ny_sl`, 1 BTC | jedno okno z piatich, +0,003 pp break-even |
| [OPTIMALIZACIA](OPTIMALIZACIA_2026-09-05.md) §6 | `btcusdt_3m_binance_ny_sl_risk1` | jedno okno z piatich, −1,54 → −0,91 % |
| [OPTIMALIZACIA](OPTIMALIZACIA_2026-09-05.md) §4 | `ethusdt_3m_binance_ny_sl`, 1–2 ETH | dve okná z piatich, mierne lepšie |
| [OPTIMALIZACIA](OPTIMALIZACIA_2026-09-05.md) §6 | `ethusdt_3m_binance_ny_sl_risk1` | 2021-22 −0,21 → +1,17 %, teda **5 z 5 rokov ziskových** (predtým 4 z 5) |
| [SEANSY](SEANSY_2026-09-05.md) | `btcusdt_3m_binance_ny`, `_struct` | líši sa od dokumentu, ale dokument je spred opráv adaptéra z 5. 9. — porovnateľné nie je; závery držia |
| [MERANIE_ibs_nas100usd](MERANIE_ibs_nas100usd_2026-09-11.md) | parametre behov z 9/2026 na NAS100, emulátor | **bez zmeny**, 5 z 5 okien zhodných |
| [PARITA_ibsninja](PARITA_ibsninja_2026-09-20.md) (NAS100 časť) | `nas100_dukas_3m`, emulátor | **bez zmeny** v oboch oknách, ku ktorým je pôvodný beh |
| [SYNTETICKY_trh](SYNTETICKY_trh_2026-09-10.md) | `btcusdt_3m_binance_ny_sl_risk1` na `SYNTH/USDT:USDT` | veľká zmena, ale **nespôsobila ju oprava**: 3m súbor syntetického trhu sa prestaval až po meraní (pozri nižšie) |

Opravy pohli IBS na Freqtrade len na začiatkoch okien a pri market vstupoch: 0 až 2 okná
z piatich na konfiguráciu, vždy pri rovnakom alebo takmer rovnakom počte obchodov. Žiadny
záver pôvodných dokumentov sa neobracia. Strop N-LIVE-20 neodstránil v risk profiloch ani
jeden obchod (počty sedia), lebo pri `minSlDistance 0,20 %` a páke 10 je 1 % riziko vždy
splniteľné. Emulátor MultiCharts dáva na IBS NAS100 bit po bite to isté, čo pred opravou.

## OPTIMALIZACIA — BTC `btcusdt_3m_binance_ny_sl` (1 BTC, `legacyPineSizing`)

Pôvodné = posledné behy pred opravou (19. 9., po oprave plnenia market vstupov v `EngineRunner`).
Dokument má staršie čísla z 5. 9. (break-even 0,3109 / 0,0592 / −0,0075 / 0,1572 / 0,2349).

| okno | obchody | PnL % pôv. → nové | break-even % pôv. → nové | beh |
|---|---|---|---|---|
| 2021-10 → 2022-10 | 28 → 28 | +12,54 → +12,54 | 0,2615 → 0,2614 | `20261026-124524-4d4e57` |
| 2022-10 → 2023-10 | 34 → 34 | +1,37 → +1,37 | 0,0707 → 0,0707 | `20261026-124549-9c6253` |
| 2023-10 → 2024-10 | 37 → 37 | −3,10 → **−2,90** | 0,0078 → **0,0107** | `20261026-124612-de24ea` |
| 2024-09 → 2025-09 | 28 → 28 | +4,49 → +4,49 | 0,1341 → 0,1341 | `20261026-124635-bc959a` |
| 2025-09 → 2026-09 | 22 → 22 | +7,88 → +7,88 | 0,2227 → 0,2227 | `20261026-124449-0e0104` |

Okno 2023-24 na kóde pred opravou dá znova −3,10 % / 0,0078, takže rozdiel spôsobila oprava.
Záver dokumentu (filter tesného SL, rok 2023-24 bez edge) platí.

## OPTIMALIZACIA §6 — BTC `btcusdt_3m_binance_ny_sl_risk1` (1 % riziko)

Pôvodné = behy analytiky z 10. 9.; posledné okno = beh `20260909-174120-e99eab` z [BURZA](BURZA_tester_vs_binance_2026-09-09.md).

| okno | obchody | PnL % pôv. → nové | break-even % pôv. → nové | max DD % | beh |
|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 28 → 28 | +22,13 → +22,12 | 0,2072 → 0,2072 | 7,83 | `20261026-124657-a4ebf1` |
| 2022-10 → 2023-10 | 34 → 34 | −1,41 → −1,41 | 0,0444 → 0,0444 | 12,00 | `20261026-124720-bc411a` |
| 2023-10 → 2024-10 | 37 → 37 | −1,54 → **−0,91** | 0,0432 → **0,0464** | 10,16 | `20261026-124749-a56bbe` |
| 2024-09 → 2025-09 | 28 → 28 | +11,70 → +11,70 | 0,1405 → 0,1406 | 5,63 | `20261026-124818-e8f510` |
| 2025-09 → 2026-09 | 22 → 22 | +11,91 → +11,89 | 0,1568 → 0,1567 | 3,83 | `20261026-124846-334951` |

Súčet +42,8 → +43,4 %, ziskové ostávajú 3 z 5 rokov.

## OPTIMALIZACIA §4 — ETH `ethusdt_3m_binance_ny_sl` (1–2 ETH, `legacyPineSizing`)

Pôvodné = tabuľka v dokumente (bez behov v histórii, spúšťané holým Freqtrade).

| okno | obchody | PnL % pôv. → nové | break-even % pôv. → nové | beh |
|---|---|---|---|---|
| 2021-10 → 2022-10 | 26 → 26 | +0,13 → **+0,25** | 0,0612 → **0,0699** | `20261026-124915-402b40` |
| 2022-10 → 2023-10 | 36 → 36 | +0,71 → +0,71 | 0,1085 → 0,1085 | `20261026-124944-9da70c` |
| 2023-10 → 2024-10 | 33 → 33 | +1,30 → +1,30 | 0,1224 → 0,1224 | `20261026-125013-9275db` |
| 2024-09 → 2025-09 | 42 → 42 | +0,35 → +0,37 | 0,0658 → 0,0665 | `20261026-125042-f14933` |
| 2025-09 → 2026-09 | 27 → 27 | +1,18 → +1,18 | 0,1342 → 0,1342 | `20261026-125110-2cd776` |

## OPTIMALIZACIA §6 — ETH `ethusdt_3m_binance_ny_sl_risk1` (1 % riziko)

| okno | obchody | PnL % pôv. → nové | break-even % (nové) | max DD % pôv. → nové | beh |
|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 26 | −0,21 → **+1,17** | 0,0617 | 8,0 → 7,86 | `20261026-125139-d5cef7` |
| 2022-10 → 2023-10 | 36 | +6,81 → +6,80 | 0,0924 | 5,0 → 4,98 | `20261026-125206-05a225` |
| 2023-10 → 2024-10 | 33 | +17,10 → +17,10 | 0,1623 | 6,9 → 6,92 | `20261026-125231-42cee1` |
| 2024-09 → 2025-09 | 42 | +14,55 → +14,83 | 0,1235 | 5,3 → 5,26 | `20261026-125254-8b8c5b` |
| 2025-09 → 2026-09 | 27 | +2,26 → +2,26 | 0,0693 | 7,8 → 7,81 | `20261026-125316-3ad96c` |

Okno 2021-22 na kóde pred opravou dá znova −0,21 % (break-even 0,0489), takže zmenu spôsobila oprava.
Súčet +40,5 → +42,2 %, ziskových rokov je **5 z 5** namiesto 4 z 5. Dokument pôvodne
break-even pri risk sizingu neuvádzal.

## SEANSY — BTC `btcusdt_3m_binance_ny` a `btcusdt_3m_binance_struct` (1 BTC)

Dokument je spred opráv adaptéra z 5. 9. ([OPRAVY_adapter](../audity/OPRAVY_adapter_2026-09-05.md)). Na
porovnanie s „len NY“ je preto vedľa stĺpec „pred“ z OPTIMALIZACIA §1, ktorý je už po nich.

| okno | NY obch. | NY break-even % SEANSY / OPTIM. / nové | NY PnL % OPTIM. → nové | NY beh |
|---|---|---|---|---|
| 2021-10 → 2022-10 | 40 | 0,207 / 0,2072 / **0,1910** | +11,09 → +11,84 | `20261026-125339-16177b` |
| 2022-10 → 2023-10 | 56 | 0,062 / 0,0568 / 0,0683 | +1,83 → +1,98 | `20261026-125402-c762b0` |
| 2023-10 → 2024-10 | 46 | 0,014 / −0,0023 / **0,0159** | −3,37 → −3,15 | `20261026-125425-92d8f8` |
| 2024-09 → 2025-09 | 40 | 0,082 / 0,0820 / 0,0707 | +1,48 → +1,48 | `20261026-125447-11f31a` |
| 2025-09 → 2026-09 | 34 | 0,142 / 0,1332 / 0,1357 | +5,92 → +5,92 | `20261026-125510-553bdc` |

Spolu 216 obchodov (OPTIMALIZACIA 215). Čísla z 5. 9. sa medzičasom pohli aj inými opravami
(plnenie market vstupov v `EngineRunner` 19. 9.), takže tento rozdiel nie je čistý efekt auditu.

| okno | struct obch. | struct break-even % SEANSY → nové | struct PnL % SEANSY → nové | beh |
|---|---|---|---|---|
| 2021-10 → 2022-10 | 92 | 0,140 → 0,1057 | +13,97 → +10,74 | `20261026-125533-f93a1e` |
| 2022-10 → 2023-10 | 114 | −0,003 → 0,0226 | −4,82 → −6,29 | `20261026-125557-2e1ec9` |
| 2023-10 → 2024-10 | 111 | 0,016 → 0,0253 | −4,39 → −5,55 | `20261026-125624-f25195` |
| 2024-09 → 2025-09 | 95 | 0,040 → 0,0393 | −2,49 → −2,15 | `20261026-125651-9d229a` |
| 2025-09 → 2026-09 | 85 | 0,057 → 0,0582 | +0,58 → +1,35 | `20261026-125718-5ba6fb` |

Spolu 497 obchodov (494 v OPTIMALIZACIA). Záver SEANSY drží: NY je kladné vo všetkých piatich
rokoch, obe seansy spolu majú break-even pod taker poplatkom v štyroch z piatich.

## MERANIE_ibs_nas100usd — IBS na NAS100/USD cez emulátor MultiCharts

Behy dokumentu majú profil `golden_coinbase_btcusd_3m`, ale s parametrami z ladenia `tuneL2`
(RR 1,3, bez trailingu a pin baru, `minImbSizePoints 3,5`…). Dnešný profil s rovnakým menom je
iný, preto sa prepočítavalo s parametrami pôvodného behu `20260910-220626-d68bad`, fee 0.

| okno | obchody | PnL % | break-even % pôv. → nové | beh |
|---|---|---|---|---|
| 2021-10 → 2022-10 | 52 → 52 | +5,645 → +5,64 | 0,0400 → 0,0400 | `20261026-130300-f0b4c2` |
| 2022-10 → 2023-10 | 55 → 55 | +1,525 → +1,52 | 0,0106 → 0,0106 | `20261026-130319-fa6532` |
| 2023-10 → 2024-10 | 57 → 57 | +9,973 → +9,97 | 0,0496 → 0,0496 | `20261026-130331-5525eb` |
| 2024-09 → 2025-09 | 66 → 66 | +5,258 → +5,26 | 0,0189 → 0,0189 | `20261026-130344-4a36d0` |
| 2025-09 → 2026-09 | 62 → 62 | +10,616 → +10,62 | 0,0319 → 0,0319 | `20261026-130357-8ebfa2` |

Bez zmeny. Omylom spustené aj s dnešným profilom `golden_coinbase_btcusd_3m`
(`20261026-125742-e98ffe`, `-125753-0efd5c`, `-125804-6c4204`, `-125815-996372`, `-125827-4ede53`):
107–141 obchodov za rok a break-even okolo nuly. To nie je efekt opravy, ale iný profil.
Z histórie sa nemazali.

## PARITA_ibsninja — `nas100_dukas_3m` cez emulátor

| okno | obchody | PnL % | break-even % | max DD % | beh | pôvodný beh |
|---|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 117 | −12,41 | −0,0017 | 35,2 | `20261026-125839-263c75` | — |
| 2022-10 → 2023-10 | 123 | −20,87 | −0,0024 | 51,1 | `20261026-125852-3de039` | — |
| 2023-10 → 2024-10 | 128 | +67,42 | 0,0055 | 13,9 | `20261026-125903-f73455` | — |
| 2024-09 → 2025-09 | 157 | +69,93 | 0,0048 | 27,8 | `20261026-125917-ac71bc` | `20260919-221817-03e8f3`: zhodné |
| 2025-09 → 2026-09 | 118 | +42,68 | 0,0046 | 17,2 | `20261026-125930-99e306` | `20260911-201127-d9a8b9`: zhodné |

Oba okná s pôvodným behom vyšli do posledného čísla rovnako. Profil je MNQ referencia
(RR 1, trailing), nie ladené nastavenie, takže o edge sa z toho nič neusudzuje.

## SYNTETICKY_trh — `btcusdt_3m_binance_ny_sl_risk1` na `SYNTH/USDT:USDT`

| okno | obchody pôv. → nové | break-even % pôv. → nové | PnL % nové | beh |
|---|---|---|---|---|
| 2021-10 → 2022-10 | 16 → 23 | +0,1104 → −0,0017 | −7,53 | `20261026-130021-e67230` |
| 2022-10 → 2023-10 | 21 → 36 | −0,0597 → −0,0316 | −18,77 | `20261026-130044-efe972` |
| 2023-10 → 2024-10 | 0 → 26 | — → +0,0063 | −7,54 | `20261026-130111-02a7d1` |
| 2024-09 → 2025-09 | 5 → 32 | −0,1789 → −0,0028 | −9,88 | `20261026-130141-c30602` |
| 2025-09 → 2026-09 | 9 → 40 | +0,1109 → −0,0308 | −17,25 | `20261026-130214-585425` |

Kód pred opravou dá v okne 2022-23 tiež 36 obchodov (break-even −0,0317), takže **zmenu
nespôsobila oprava**. Pôvodné behy bežali 10. 9. o 10:12 UTC, ale 3m a 5m súbor
`data/tester/synthetic/futures/SYNTH_USDT_USDT-3m-futures.feather` je z 10. 9. 15:11
miestneho času (13:11 UTC). Behy z dokumentu teda počítali na inom 3m grafe syntetického
trhu než dnešný sklad. 1m súbor a recept (`sha256 b29861a1…`) sú tie isté.

- Hlavný záver dokumentu platí a je silnejší: na syntetickom trhu je teraz **každé okno záporné**
  alebo na nule (namiesto 2 kladných zo 4) a engine si edge nevymýšľa.
- **Vedľajší nález neplatí.** Plnilo sa vtedy 0–57 % signálov proti 72–95 % na BTC, a z toho
  vznikla hypotéza, že limitka na úrovni medzery sa na premiešanom trhu nevyplní. Teraz sa
  plní 23–40 obchodov ročne, teda porovnateľne s BTC. Pôvodné nízke plnenie bolo
  pravdepodobne artefakt 3m dát v tej chvíli. Hypotézu treba pred použitím zmerať znova.

## Čo sa neprepočítavalo a prečo

| dokument | prečo nie |
|---|---|
| [BACKTEST_rok_btcusdt](BACKTEST_rok_btcusdt_2026-09-04.md), [BACKTEST_rok_rr25_all3](BACKTEST_rok_rr25_all3_2026-09-04.md), [SWEEP_rr_a_tf](SWEEP_rr_a_tf_2026-09-04.md), [FILTRE_vstupu](FILTRE_vstupu_2026-09-04.md), [HYPOTEZA_koniec_seansy](HYPOTEZA_koniec_seansy_2026-09-04.md) | Historické kroky spred opráv adaptéra z 5. 9. Ich výsledok žije ďalej v profiloch `struct`, `ny`, `ny_sl`, ktoré sa prepočítali vyššie. |
| [HYPEROPT_btcusdt](HYPEROPT_btcusdt_2026-09-04.md), [HYPEROPT_uzky](HYPEROPT_uzky_2026-09-04.md) | Hľadanie parametrov. Záver „overfituje / nenašiel nič“ sa posunom pár obchodov nezmení. |
| [AI_filter](AI_filter_2026-09-10.md), [KALENDAR_dni_a_makro](KALENDAR_dni_a_makro_2026-09-10.md), [REZIM_filtre_btcusdt](REZIM_filtre_btcusdt_2026-09-10.md) | Filtre nad obchodmi `ny_sl_risk1` na BTC. Základ sa pohol len v jednom okne (2023-24), a to o 0,003 pp. |
| [EXEKUCIA_maker_taker](EXEKUCIA_maker_taker_2026-09-05.md), [PAKA](PAKA_2026-09-05.md) | Metodika (podiel maker vstupov, mierka páky) na `struct` profile. Neopiera sa o presné počty. |
| [BURZA_tester_vs_binance](BURZA_tester_vs_binance_2026-09-09.md) | Porovnáva burzy navzájom, nie s minulosťou. Oprava pôsobí na obe rovnako. |
| [PARITA_pnl_tradingview](PARITA_pnl_tradingview_2026-09-08.md) | Parita s TradingView. Stráži ju golden test (`tester/tests/test_golden_tv_binance.py`), ktorý pri oprave prešiel. |
| [PARITA_orbninja](PARITA_orbninja_2026-09-24.md) | Parita Python ↔ C# (`tester/tests/test_csharp_parity.py`), nie meranie edge. |
| [NAS100_dukas_simulator](NAS100_dukas_simulator_2026-09-06.md) | Porovnanie simulátora s MultiCharts betou na jednom mesiaci, nie meranie edge. Emulátor na tom istom profile vyšiel bez zmeny (pozri PARITA_ibsninja vyššie). |
