# Systematický prechod Pine skriptu (2026-09-05)

Trailing stop aj `closeAtSessionEnd` sa našli **náhodou** — až keď ich iná
konfigurácia spustila. To je zlý spôsob hľadania, tak sme celý skript prešli
mechanicky.

## Ako sa hľadalo

**1. Každý `input` proti configu a proti použitiu.** Skript vytiahol všetkých
115 Pine inputov a pre každý overil, či existuje pole v `IBSConfig` a či ho
niekto v `ibs/` naozaj číta (samotná deklarácia v `config.py` sa neráta). Presne
tento test by bol trailing aj `closeAtSessionEnd` odhalil.

**2. Sekcie a funkcie.** Všetky `// ==== NÁZOV ====` bloky a všetky Pine funkcie
(`f_...() =>`) proti náprotivku v porte.

**3. Volania, ktoré niečo robia.** `strategy.*`, `plot*`, `bgcolor`, `barcolor`,
`alert`, `box.*`, `label.*`.

## Čo chýbalo

### 1. Koniec seansy neutínal zóny v STATE 0-3 *(mení obchody)*

Pine 2271–2288: na konci **každej** seansy sa zóna, ktorá sa ešte len formuje
(STATE 0–3, teda ešte bez orderu), invaliduje. Bez toho prežije medzeru medzi
dvoma seansami a obchoduje sa v tej nasledujúcej — a box sa na grafe ťahá cez
viacero seáns.

Náš engine `trade_window_just_closed` **počítal, ale nikto ho nečítal**. Pole
existovalo od začiatku, len viselo vo vzduchu — rovnaký vzor ako pri trailingu.

Doplnené ako `StateMachine.cut_forming_zones()`. Na profile
`btcusdt_3m_binance_struct` sa spustí **837× za rok** (817 zón v STATE 0, 17
v STATE 2, 1 v STATE 3), ale **počet ani výsledok obchodov nemení** — tie zóny by
sa aj tak k orderu nedostali. Je to teda oprava správnosti a kreslenia, nie
výsledku; na inej konfigurácii (dlhšia platnosť zón, iné seansy) by ale rozdiel
spraviť mohla.

### 2. Vyplnenie orderu neuzavieralo zónu *(kreslenie)*

Pine 2185: `if invalidateOnFill or zPendingInvalid → resizeZoneOnInvalidation`.
Box zóny sa pri vyplnení orderu utne. `invalidateOnFill` je zapnutý defaultne
a v porte sa nepoužíval vôbec; `pending_invalid` sa nastavoval, ale nikdy nečítal.

### 3. Nekreslil sa box na sviečke, ktorá vytvorila gap *(kreslenie)*

Pine 682–701 hľadá ten istý trojsviečkový vzor na **každom** bare, nezávisle od
zón, a kreslí box na telo prostrednej sviečky. `DrawKind.IMB_BOX` v porte
existoval, ale nikto ho nikdy nevytvoril.

Nedá sa nahradiť zónovým `detect_imbalance()` — ten rieši inú otázku (či sa gap
dá priradiť ku konkrétnej zóne) a beží len pre zóny.

## Čo chýba zámerne

| oblasť | Pine | prečo nie |
|---|---|---|
| PickMyTrade | `pmtToken`, `pmtAccountId`, `pmtStratName`, `pmtMarketOrderType`, `trailFreqPct`, 5× `alert()` | posielanie orderov externému brokerovi; Freqtrade aj MultiCharts majú vlastné |
| Dashboard | `showDashboard`, `dashPos`, `dashboardRows`, `f_mergedCell` | `table.cell()` sa nedá zmysluplne portovať ani logovať |
| Log obchodov | `showTradeLog`, `tradeLogRows`, `addLogEntry`, `setLogStatus` | to isté; ekvivalent je `ibs.tools.report` |
| Debug tabuľka | `showDebugTable`, `debugTableRows`, `debugPos` | to isté |
| Alert prepínače | `alertOnState2/3/4` | alerty sa neportujú |
| `barcolor` fade IMB | Pine 686 | zafarbenie sviečky, nie objekt — nemá `DrawKind` |
| `state4MaxBars` | Pine 203 | **v Pine samotnom nepoužitý** („Rezerva (aktuálne nepoužívané)") |

Sessions 2 a 3 vyzerali v prvom prechode ako nepoužité, ale sú to falošné
poplachy — `SessionClock` k nim pristupuje cez `getattr(cfg, f"sess{n}...")`.

## Ponaučenie

Všetky tri nálezy majú ten istý tvar: **konfigurácia, na ktorej sa merala parita,
tú vetvu nikdy nespustila.** Golden test s RR 1 nespustil trailing, nespustil
`closeAtSessionEnd`, a jeho zóny nikdy neprežili medzeru medzi seansami.

Parita na jednej konfigurácii teda nie je dôkaz úplnosti portu. Test „každý input
musí niekto čítať" je slabší, ale odhalí presne tú triedu chýb, ktorú parita
prehliadne — a stojí pár sekúnd. Skript je v histórii tohto commitu; oplatí sa ho
spustiť po každom väčšom zásahu do Pine skriptu.

Regresné testy: `ibs/tests/test_pine_audit.py`.
