# Životný cyklus orderu v živých adaptéroch

Tri adaptéry vykonávajú ten istý automat nad vstupom z enginu: `LiveInstance` v NinjaTraderi
(`tradebot/adapters/ninjatrader/TradeBotLiveInstance.cs`), EA stratégie v MT5 (`tradebot/adapters/mt5/TradeBotEA.mqh`)
a exekútor route (`tradebot/adapters/mt5/TradeBotExecutor.mqh`). Každý vznikal zvlášť a audity opakovane našli
opravu, ktorá sa spravila len v jednom z nich (routing K1 → M-LIVE-3, M-LIVE-7). Tento dokument je jedna tabuľka
stavov a pravidiel pre všetky tri: **zmena pravidla v jednom adaptéri = tá istá zmena v ostatných dvoch**, alebo
riadok v tabuľke „Rozdiely" s dôvodom.

Signály a parita bar po bare sa tohto netýkajú ([NINJATRADER.md](NINJATRADER.md), [MT5.md](MT5.md)); tu ide o exekúciu.
Správanie NinjaTradera overuje simulátor porúch ([SIMULATOR_PORUCH.md](SIMULATOR_PORUCH.md)), MQL5 len preklad a demo.

## Stavy

| Stav | Význam | NT `Tracked` | EA `Tracked` | Exekútor `XOrder` |
|---|---|---|---|---|
| odložený | vstup čaká, kým skončí bežiaca pozícia; u brokera nie je | `Parked` | `parked` | — (odkladá master v NT) |
| čakajúci | vstup je u brokera, nevyplnený | `Entry` žije | `orderTicket > 0` | `ticket > 0`, `!filled` |
| ruší sa | zrušenie odišlo, broker ho nepotvrdil | záznam v `_dying` | `cancelWanted` | `cancelWanted` |
| vyplnený, chránený | pozícia beží, SL/TP stoja u brokera | `Filled`, `Sl`/`Tp` žijú | `filled`, netting `slTicket`/`tpTicket`, hedging SL/TP na pozícii | `filled`, SL/TP na pozícii |
| vyplnený, bez stopu | SL u brokera nestojí (odmietnutý, zrušený zvonka) | `NoStopSince` | `noStopSince` | `noStopSince` |
| zatvára sa | trhový výstup beží alebo sa skúša znova | `Closing` (+ `Protect`) | `closing` (+ `protect`) | `closing` |
| zatvorený | objem 0, záznam zaniká | odstránený z `_orders` | `RemoveOrder` | `RemoveOrder` |

## Pravidlá

| # | Pravidlo | NT | EA | Exekútor |
|---|---|---|---|---|
| 1 | Order sa prestane sledovať až po **potvrdenom** koncovom stave, nie po odoslaní zrušenia | `_dying`, `HandleOrder` | `EntryCancelState` | `ReconcileOrder` pred zrušením |
| 2 | Výplň vstupu, ktorý sa mal zrušiť, sa prevezme a hneď zavrie trhom | `AdoptLate` | `RetryGuards` (`cancelWanted` + `filled`) | `CancelEntry` → `fill` do NT |
| 3 | Nový vstup s tým istým id ide až po potvrdenom konci starého | čaká na `_dying` | starý sa ruší v `Apply` | `ReplaceEntry` |
| 4 | Pozícia nesmie ostať bez stopu: po 2 s sa položí znova, po 3 neúspechoch sa zavrie trhom | `GuardExits` | `GuardStop` | `GuardStop` |
| 5 | Pred trhovým výstupom sa SL/TP zrušia; čo sa nepotvrdí, sa stráži ďalej, aby stop neostal bez pozície | `Drop` → `_dying` s `Exit` | `CancelExits` / `ClosePosition` | SL/TP zanikajú s pozíciou (hedging) |
| 6 | Odmietnutý trhový výstup sa skúša znova s rastúcim odstupom; po 3 neúspechoch stoja medzi pokusmi SL/TP znova | `CloseFailed`, `Protect` | `ClosePosition`, `protect` | `ClosePosition` (SL/TP ostávajú) |
| 7 | Zvyšok čiastočne vyplneného vstupu sa pri zatváraní zruší; ďalšia čiastočná výplň navýši objem SL/TP bez osirelej dvojice | `RequestClose`, `EnsureExits` | `PlaceExits` (najprv zruší starú dvojicu) | `DropRemainder` |
| 8 | Stav spred reštartu sa zlaďuje až po pripojení k brokerovi; zdroj pravdy je broker | `RestoreState` po predhistórii | `FinishRestore` (4 s po pripojení) | `Reconcile` po `TERMINAL_CONNECTED` |
| 9 | Za behu: čo adaptér sleduje, musí u brokera byť — pri stabilnom spojení (30 s) a po 10 s bez správy sa dohľadá v histórii | `ReconcileExternal` | `ReconcileBroker` | `PositionGone`, strážca čakajúcich v `Guards` |
| 10 | Výpadok spojenia nie je zatvorenie: kým účet nie je zosynchronizovaný, „pozícia chýba" sa neposudzuje | `_connectedSince` | `g_connectedSince`, `ConnectSettleSec` | `g_connectedSince`, `ConnectSettleSec` |
| 11 | Koniec dňa (EOD) sa vykoná podľa hodín, aj keď bar neprišiel | `EodByClock` | `EodByClock` | termíny `life` z mastera |
| 12 | Zatváranie prerušené reštartom sa po štarte dokončí | `closing` v stave, `RequestClose` po prevzatí | `closing` v stave, `ClosePosition` po prevzatí | `closing` len v pamäti; master pošle `close` znova |
| 13 | Chyba, ktorú adaptér nevie vyriešiť, ide do hubu ako `note error` s tlmením, nie len do logu platformy | `Note`, `NoteThrottled` | `Report`, `EngineFail` | `Note` |

## Rozdiely, ktoré sú zámer

- **Exekútor nepodporuje netting** — route na netting účet odmietne, takže pravidlá o vlastných SL/TP orderoch
  (5, 7) rieši broker pozíciou.
- **Odkladanie vstupov** (Pine `pyramiding=0`) je vec mastera; exekútor dostane vstup, až keď ho master pustí.
- **Pravidlo 12 v exekútore** rieši master: exekútor `closing` do stavu nepíše, po návrate ho NT zosúladí (`sync`)
  a `close` pošle znova.
- **Samooprava radu barov** (`feed_dead`) je len v NT: MT5 bary berie z terminálu a mŕtvy feed tam hlási `FeedWatch`.

## Keď sa mení pravidlo

1. Uprav riadok tabuľky a všetky tri stĺpce (alebo zapíš rozdiel s dôvodom).
2. NT: pridaj scenár do `tester/tests/test_ninjatrader_faults.py` — najprv scenár, ktorý chybu ukáže, potom oprava.
3. MT5: prelož EA aj exekútor z repa (`python -m tradebot.adapters.mt5 check` prekladá nainštalované kópie, nie repo)
   a prejdi scenár na deme — simulátor MQL5 nepokrýva.
