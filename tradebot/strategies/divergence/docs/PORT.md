# Port `DivergenceStrategy` (Freqtrade, 2022) do TradeBotu

Zdroj: `freqtrade-strategies/user_data/strategies/divergence_strategy.py` (2 582 riadkov,
z toho väčšina zakomentovaná alebo nepoužitá) plus naladené configy
`user_data/config/config_div_*_15m.json`. Tento dokument hovorí, **čo z toho v porte je,
čo sa zmenilo a čo sa vedome vynechalo** — aby sa dalo pri každom rozdiele v backteste
povedať, či je to chyba portu alebo rozhodnutie.

## Čo stratégia robí (to, čo bolo v origináli naozaj aktívne)

1. **Divergencie na grafe** (15m, Heikin Ashi): algoritmus „Divergence for Many Indicators v4"
   (LonesomeTheBlue) prepísaný do pandas. Indikátory MACD, MACD hist., RSI, stochastik, CCI,
   momentum, OBV, VW MACD, CMF, MFI, CDV — zvlášť prepínateľné pre long a short.
2. **Filtre vstupu** (`populate_entry_trend`): divergencia na niektorom z posledných 3 barov
   a žiadna opačná; RSI ≤ 60 (long) / ≥ 40 (short); supertrend na 1h aj 4h v smere obchodu;
   supertrend na 5m proti smeru vnútri baru grafu (pullback); žiadna opačná divergencia
   na 4h za posledných 44 barov a na 1h za posledných 6 barov („zóny").
3. **Vstup**: `confirm_trade_entry` s „trailing buy" — prvé volanie len založí referenciu,
   vstúpi sa až keď je cena vyššia (long) než referencia, najviac 3 bary.
4. **Výstup** (`custom_stoploss`, `use_exit_signal = False`, ROI 90 % = nikdy):
   stratový obchod sa zavrie, keď 4h supertrend otočí alebo cena prerazí jeho čiaru, alebo
   keď strata presiahne 200 $; ziskový obchod: od 1,5 % zisku stop na +0,35 % (zámok),
   od 4 % zisku stop 1 % pod cenou (trailing). Tvrdý stop −55 %.
5. Páka `strat_lvrg` (2,5 v naladenom configu).

## Mapovanie na TradeBot

| originál | port | poznámka |
|---|---|---|
| `prd`, `source`, `search_div`, `max_pp`, `max_bars`, `dont_confirm` | `prd`, `source`, `searchDiv`, `maxPp`, `maxBars`, `dontConfirm` | rovnaký význam |
| `calc_<ind>_buy` / `calc_<ind>_sell` | `div<Ind>Long` / `div<Ind>Short` | 11 indikátorov × 2 strany |
| `buy_num_divs`, `sell_num_divs` | `minDivsLong`, `minDivsShort` | |
| `shift(0..2)` divergencie | `signalBars = 3` | |
| supertrend (15, 4) na grafe, (15, 3,5) na 1h a 4h | `stLen`, `stMult`, `stMultHtf`, `htfMinutes`, `htf2Minutes` | |
| `st_down_c > 0` (5m bary v protismere) | `pullbackFilter` | viď rozdiely |
| `pair_bear_zone` (4h, 44) / `pair_bear_zone_ltf` (1h, 6) | `zoneFilter`, `zonePrd1/2`, `zoneWindow1/2`, `zoneMaxPp`, `zoneMaxBars`, `zoneSearchDiv` | |
| RSI ≤ 60 / ≥ 40 | `rsiLen`, `rsiLongMax`, `rsiShortMin` | |
| trailing buy v `confirm_trade_entry` | `entryMode = confirm` | viď rozdiely |
| `max_abs_loss = -200` | `riskDollar = 200` + `slAtrMult` | viď rozdiely |
| trend v `custom_stoploss` (profit ≤ 0) | `trendExit` | |
| zámok 1,5 % → +0,35 %, trailing 4 % / 1 % | `enableTrailing`, `beActivationPct`, `beLockPct`, `trailActivationPct`, `trailOffsetPct` | `TwoStageTrailing` |
| `strat_lvrg` | `leverage` (profil) | rozšírenie portu |

Defaulty configu sú z `config_div_btc_15m.json` (posledný hyperopt), nie z tela triedy —
tam boli všetky indikátory vypnuté a stratégia by nedala ani jeden obchod.

## Rozdiely, ktoré menia signály

1. **Pivoty bez pohľadu dopredu.** Originál bral pivoty z `argrelextrema` nad celým
   DataFrame, teda pivot poznal už na bare, kde nastal — `prd` barov skôr, než ho trh
   potvrdil. Port použije pivot až po potvrdení (Pine `ta.pivothigh`). Divergencie tak
   prichádzajú o `prd` barov neskôr a backtest je poctivý. Toto je najväčší rozdiel.
2. **Zóny na vyšších TF rátali len regulárne divergencie.** Originál mal pre zóny nastavené
   `hid = reg = True`, ale v `search_divergences` sa `*_HID_COUNT` zvyšoval pri podmienke
   `POS_REG`, takže skryté sa nikdy nezarátali a regulárne dvakrát. `zoneSearchDiv =
   regular` je to, čo stratégia naozaj robila; `regular/hidden` je to, čo mala v úmysle —
   a blokuje takmer všetko (na 3 mesiacoch BTC 15m 97 % barov).
3. **Pullback z grafového TF, nie z 5m.** `st_down_c` počítalo 5m bary v protismere vnútri
   baru grafu. Nižší TF sa z barov grafu poskladať nedá a rámec má jeden informatívny TF
   (Data2), takže sa berie supertrend grafového TF proti trendu vyšších TF. Na 5m grafe je
   to identické; na 15m je to prísnejšie (celý bar v protismere, nie jeden z troch).
4. **Vyššie TF sa skladajú v engine** z barov grafu (`htf.py`), rovnakým pravidlom ako
   `tradebot/core/candles.py`. HTF bar je dostupný na prvom bare grafu novej periódy —
   presne ako `merge_informative_pair`. TF grafu preto musí deliť 60 aj 240 minút.
5. **Vstup s potvrdením** je model trailing buy na uzavretých baroch: kým signál trvá
   (divergencia žije `signalBars` barov a filtre držia), každý bar sa porovná close
   s close predchádzajúceho baru a prvý bar v smere obchodu vstupuje. Originál to isté
   robil v `confirm_trade_entry` s otváracími cenami sviečok (open N+1 ako referencia,
   vstup na open N+2, ak je vyššie) — o jednu cenu posunuté (close N ≈ open N+1). Keď signál
   zmizne, čakanie končí; originál nechal záznam v slovníku a pri ďalšom signáli ho
   zahodil ako starý.
6. **Stop a veľkosť.** Originál stop prakticky nemal (−55 %) a stratu držal limit 200 $
   pri pevnom stake. TradeBot vyžaduje stop v pláne (MultiCharts order, analytika, sizing
   z rizika): stop je `slAtrMult` × ATR a `riskDollar = 200` určuje veľkosť pozície tak, aby
   strata na stope bola tých 200 $. Výsledok je prenositeľný na iný účet; originál nebol.
7. **Trailing v percentách ceny.** Originál násobil prahy pákou (`0.015 * strat_lvrg`),
   lebo Freqtrade `current_profit` je z marže; v cene je to tých 1,5 % / 0,35 % / 4 % / 1 %.
8. **Heikin Ashi štandardná** (`ha_high = max(high, ha_open, ha_close)`); qtpylib bralo do
   `ha_high` surové open/close. Supertrend je Pine `ta.supertrend`; RMA/EMA sa rozbiehajú
   z SMA (talib), nie z prvej hodnoty. Drobné rozdiely v rozbehu, nie v logike.

## Čo sa vynechalo (v origináli neaktívne alebo neprenositeľné)

- **DCA / safety orders** (`calc_safety_step_strategy`, `adjust_params_pair`, fib úrovne
  zo zigzagu 1h): stratégia nemala `adjust_trade_position`, takže nič z toho nebežalo.
- **Trailing sell** v `confirm_trade_exit`: platil len pre `roi`/`sell_signal`, ktoré
  s `use_exit_signal = False` a ROI 90 % nikdy nenastali.
- **MACD S/R, zigzag na grafe, dynamický lineárny regresný kanál, HA trend 4h, RSI 4h,
  Bollinger vzdialenosti**: počítali sa, ale žiadna aktívna podmienka ich nečítala
  (BB vzdialenosť sa ukladala pri trailing buy a nepoužila).
- **Divergencie BTC páru ako pomocný signál** (`additional_info_pairs`): zakomentované.
- **Cache divergencií do JSON** (`backtest = True` vetvy): optimalizácia, nie logika.
- **Objem pri CDV/OBV/CMF/MFI na CFD**: Dukascopy export nemá burzový objem; na takých
  trhoch tie indikátory merajú tickový objem klientov. Config to nezakazuje, analytika to
  ukáže.

## Overenie

- `tradebot/tests/test_divergence_engine.py`: detektor na vlastnom indikátore (regulárna
  býčia dĺžky 6, potvrdenie pivotu, prerušená spojnica, `dontConfirm`), skladanie HTF,
  supertrend, pivoty, dvojstupňový trailing, každý filter vstupu zvlášť, potvrdenie
  vstupu, výstup podľa trendu, časový limit, generický runner.
- Rýchlosť: 0,15 ms na bar 15m (3 mesiace BTC za 1,3 s), takže päť rokov je pod minútou
  bez 1m detailu.
- **Oba enginy na tom istom okne** (BTC/USDT:USDT 15m, 20250904-20260904, behy
  `20260911-213403-39f796` Freqtrade a `20260911-213452-06be95` emulátor): tri obchody
  (20. 2., 12. 3., 20. 6. 2026) sú v oboch **na minútu rovnaké** vo vstupe aj výstupe.
  Rozdiel je len na začiatku okna: Freqtrade dostane `required_history` (3 408 barov,
  ~35 dní) pred oknom, emulátor začína od prvého baru okna bez rozbehu — supertrend 4h
  a zóny (200 barov 4h) sú vtedy ešte prázdne, takže prvé dva týždne dáva iné signály
  (Freqtrade 4. 9. dva obchody, emulátor 6. 9. jeden). Pri stratégii s takto dlhým
  rozbehom treba okno emulátora čítať až od druhého mesiaca, alebo mu dať rozbeh.
