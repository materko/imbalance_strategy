# Ochrana účtu: denný stop, súčasné riziko, SL u brokera, duplicita

*SMERNICA V2 krok 12, zadanie U1 (28. 11. 2026). Všetko beží lokálne v EA a v NinjaTraderi, bez hubu a bez
Mac mini. Od hubu závisí len alarm.*

Poistka nad všetkými stratégiami na jednom účte:

1. **Denný stop −4 %.** Keď equity účtu klesne o `pct` % pod základ dňa, platí:
   - zavrú sa **všetky pozície účtu** (všetky inštancie, všetky symboly, aj ručné);
   - zrušia sa všetky čakajúce príkazy;
   - do začiatku nového dňa sa nepošle žiadny vstup.

   Základ dňa je **max(balance, equity)** z prvého pozorovania po resete. Reset je predvolene **00:00 Europe/Prague**
   (FTMO); pásmo aj čas sa dajú zmeniť, napríklad CME/Apex `America/New_York` `18:00`.
2. **Súčasné riziko ≤ 1,5 % equity.** Pred vstupom sa sčíta riziko do SL všetkých otvorených pozícií účtu a nového
   obchodu (|vstup − SL| × objem × hodnota bodu). Ak súčet presiahne limit, vstup sa neodošle a zapíše sa do logu.
   Pozícia bez SL má riziko neznáme, preto sa vtedy nový vstup tiež neodošle.
3. **SL vždy u brokera.** Príkaz ide so SL a TP (MT5 hedging na pozícii, netting a NT ako stop order). Pozícia, ktorá
   je bez SL u brokera dlhšie ako **5 s**, sa zavrie trhom a zapíše sa chyba.
4. **Duplicita.** Ten istý kľúč stratégie s tým istým profilom na dvoch účtoch, ktoré sa sčítavajú, sa pri štarte
   odmietne. Sčítavajú sa:
   - účty s rovnakým loginom v inom termináli;
   - účty zo skupiny v nastavení.
5. **Log a telemetria.** Spustenie stopu, zablokovaný vstup, odmietnutie pre riziko, zavretá pozícia bez SL,
   odmietnutý štart a vypnutý stop idú do logu platformy aj do telemetrie ako udalosť `account_guard`
   (`what` = `daily_stop` / `blocked` / `risk` / `no_sl` / `duplicate` / `off`). Telemetria ide do hubu, zrkadla
   webapp a Telegramu ([LIVE.md](LIVE.md)).
6. **Alarm (hub).** Plugin `watchdog` pošle do Telegramu správu, keď inštancia aktívneho nasadenia počas seansy
   (Ne 23:00 – Pi 21:00 UTC) neposlala heartbeat ani udalosť dlhšie ako 30 min. Pošle aj správu, keď sa vráti.

Celkový stop sa nerobí (rozhodnutie používateľa). Backtest (Freqtrade, emulátor, Python predloha) ochranu účtu
nepočíta. Kontrola rizika je len naživo; Strategy Tester MT5 a Strategy Analyzer NT ostávajú ako Tester.

## Ako to funguje

| čo | ako |
|---|---|
| knižnica | C# jadro: `TradeBot.Core.DailyStop` + `DailyStopRule` ([DailyStop.cs](../tradebot/core/ports/csharp/TradeBot.Core/DailyStop.cs)), `AccountGuard` a `DupLock` ([AccountGuard.cs](../tradebot/core/ports/csharp/TradeBot.Core/AccountGuard.cs)); pre MQL5 fasáda `StaticHost` verzia 7 (`DailyStopCheckBal`, `DailyStopSweepDue`, `PositionRisk`, `OpenRiskVerdict`, `StopOverdue`, `SpoolGuard`) |
| vstup | MT5 `ACCOUNT_EQUITY` a `ACCOUNT_BALANCE` (každý tik a `OnTimer` 2 s), NT `AccountItem.NetLiquidation` a `CashValue` (slučka AddOnu, chart stratégia každé 2 s) |
| zastavenie | equity ≤ základ × (1 − pct/100); platí do resetu, aj keď sa equity vráti |
| po zastavení | inštancia zavrie a zruší všetko svoje (`tb_daily_stop`). Po 10 s a najviac raz za 5 s v procese platformy jedna inštancia zavrie aj **zvyšok účtu**: MT5 cudzie pozície a príkazy, NT `Account.Flatten` všetkých inštrumentov. Oneskorenie bráni tomu, aby dve zatvorenia tej istej pozície v nettingu poziciu otočili. |
| nový deň | `time` v pásme `zone` |
| vypnutie | MT5 `InpDailyStop=false` alebo `InpDailyStopPct=0`, NT vlastnosť **Denný stop** vypnutá, hub bez stopu pri účte. Pri štarte sa vypíše varovanie a do telemetrie ide `account_guard off`. |

Stav stopu je pre účet **spoločný**. V procese platformy (všetky EA v jednom termináli, všetky inštancie
v NinjaTraderi) je jeden objekt na účet. Reštart a iný proces na tom istom účte pokrýva súbor
`dailystop_<účet>_<pásmo>_<HHmm>.json` v adresári stavu:

- MT5: `Common\Files\TradeBot\state`;
- NT: `Documents\NinjaTrader 8\TradeBot\state`.

Zastavenie jednou inštanciou platí pre všetky. Pri rôznych percentách rozhoduje najprísnejšie. V Strategy Testeri
MT5 je stav len v pamäti.

Zámok duplicity je súbor:

- MT5: `Common\Files\TradeBot\state\dup\<skupina>_<kľúč>_<profil>.txt`;
- NT: `state\dup_<skupina>_<kľúč>_<profil>.txt`.

Súbor nesie vlastníka (účet + terminál / inštalácia) a čas. Obnovuje sa každých 30 s a po 120 s bez obnovy
(pád bez uvoľnenia) neplatí. Ten istý účet v tom istom termináli (iný slot, reštart) duplicitou nie je. Duplicitu
medzi rôznymi strojmi lokálny zámok nevidí.

Zlé nastavenie (percento mimo 0–100, neznáme pásmo, čas nie HH:MM) **nespustí** EA
(`INIT_PARAMETERS_INCORRECT`) ani inštanciu NinjaTradera.

## Kde sa zapína

| platforma | nastavenie |
|---|---|
| hub / webapp (karta Live → Účty) | pole **Denný stop účtu (%)**, pásmo a začiatok dňa (predvolene 00:00 Europe/Prague); API `daily_stop: {"pct": 4, "zone": "Europe/Prague", "time": "00:00"}`, vypnúť `{"on": false}`. Hub hodnoty overí hneď. Driver ich dá do inputov EA a do `deploy.json`. Zmena reštartuje inštancie účtu. |
| MT5 EA | inputy `InpDailyStop` (predvolene zapnutý), `InpDailyStopPct` 4,0, `InpDailyStopZone` Europe/Prague, `InpDailyStopTime` 00:00, `InpMaxOpenRiskPct` 1,5, `InpAccountGroups` (napr. `111,222;333,444`). Hub pri svojich nasadeniach dá stop podľa účtu **výslovne**, takže zmena predvolieb nič nezapne na živom účte bez stopu v hube. |
| MT5 exekútor (smerovanie NT → MT5) | tie isté inputy `InpDailyStop*` a `InpMaxOpenRiskPct`; `InpDailyStop` je tu predvolene vypnutý, lebo hub dáva grafu exekútora inputy len pri účte so stopom. Vstup nad rizikom odmietne s dôvodom `risk`, zastavený účet s dôvodom `daily_stop`. |
| NT chart stratégia | skupina **Denný stop**: zapnutý, %, pásmo, začiatok dňa, **Max. súčasné riziko (%)** 1,5 a **Skupiny účtov** (len naživo) |
| NT AddOn | `deploy.json`, riadok inštancie: `"daily_stop": {…}` (píše hub), voliteľne `"max_open_risk_pct"` a `"account_groups"` |

## Obmedzenia a akceptácia

- **Smerovanie NT → MT5** ([ROUTING.md](ROUTING.md)): AddOn denný stop ani riziko NT účtu pri `route` nepoužije.
  Účet s peniazmi je v MT5 a ochranu drží exekútor.
- Stop sa kontroluje na tiku alebo časovači (MT5 tik / 2 s, NT 2 s). Pri rýchlom pohybe môže strata prekročiť
  hranicu o sklz zatváracích príkazov. Na pevný limit prop firmy nastav rezervu.
- **Akceptácia na deme (nie Server3) robí používateľ.** Na malom účte alebo so zníženým prahom (napr. 0,2 %) treba
  overiť štyri veci:
  - pozície sa zavrú;
  - nové vstupy sa odmietnu;
  - po reštarte EA ostane blokovanie;
  - po resete sa obchodovanie obnoví.

Testy:
- `tester/tests/test_mt5_static_host.py`: jadro cez fasádu — základ max(balance, equity), reset cez letný čas, zametanie, riziko, SL do 5 s, zámok duplicity, riadky `account_guard` / `reject`;
- `test_live_drivers_mt5.py`: inputy EA, `deploy.json`;
- `test_live_deploy.py`: hub;
- `test_hub_plugins.py`: alarm;
- `test_ninjatrader_faults.py`: AddOn v simulátore porúch.

Preklad: MetaEditor (`IBSNet.mq5`, `TradeBotExecutor.mq5`) a NT adaptéry proti DLL NinjaTradera 8.
