# Simulátor porúch adaptéra NinjaTradera

Parita bar po bare ([NINJATRADER.md](NINJATRADER.md)) overuje **signály**: že C# engine na každom bare
chce to isté, čo Python predloha. Nič nehovorí o **exekúcii** — čo adaptér urobí, keď broker order
odmietne, správa sa stratí, vstup sa vyplní po tom, čo ho stratégia zrušila, alebo spadne spojenie.
Presne tam boli nálezy auditov naživo (M-LIVE, N-LIVE) a žiadny z nich nemal test.

Simulátor (`tester/faultsim`) púšťa **skutočný** `LiveInstance`
(`tradebot/adapters/ninjatrader/TradeBotLiveInstance.cs`, nezmenený zdroják) nad:

- **náhradnými typmi NinjaTradera** (`NtStubs.cs`) — `Account` je falošný broker, ktorý udalosti drží
  vo fronte a doručuje ich podľa scenára,
- **skriptovaným enginom** (`FaultSim.cs`, kľúč `faultsim`) — na danom bare pošle presne ten zámer,
  ktorý scenár predpíše,
- **simulovaným časom** — `LiveClock` namiesto `DateTime.UtcNow` a slučka inštancie po krokoch
  (`Step`), takže 30 s čakania po reconnecte nestojí nič a beh je deterministický.

Do NinjaTradera sa z toho neinštaluje nič; v adaptéri pribudli len `LiveClock` (v NT vždy skutočné
hodiny) a vyčlenenie tela slučky do `Step()`.

**MetaTrader 5 tu nie je.** MQL5 mimo terminálu nebeží, takže EA a exekútor sa takto prehrať nedajú —
ostáva Strategy Tester a demo účet ([MT5.md](MT5.md), [ROUTING.md](ROUTING.md)). Smerovanie NT → MT5
(`route`) simulátor tiež nepokrýva.

## Spustenie

```bash
python -m tester.faultsim scenar.json -v      # stav po každom kroku, požiadavky na brokera, log inštancie
python -m pytest tester/tests/test_ninjatrader_faults.py
```

Simulátor sa preloží sám (`csc.exe` z .NET Frameworku alebo Mono) do
`tradebot/core/ports/csharp/bin/TradeBot.FaultSim.exe`; bez kompilátora sa testy preskočia.

Z Pythonu:

```python
from tester.faultsim import run, naked_steps
out = run({"engine": [...], "steps": [...]})
out["trace"][-1]      # stav po poslednom kroku
naked_steps(out)      # kroky, po ktorých bola pozícia bez stopu
```

## Scenár

```json
{"engine": [{"bar": 1, "action": "entry", "id": "L1", "type": "limit", "entry": 100, "sl": 95, "tp": 110},
            {"bar": 2, "action": "cancel", "id": "L1"}],
 "steps":  [{"do": "rule", "on": "cancel", "match": "L1", "then": "hold"},
            {"do": "bar"}, {"do": "bar"},
            {"do": "fill", "order": "L1"},
            {"do": "advance", "s": 3}]}
```

Graf je 1m, inštrument `SIM 03-27` (tick 0,25), účet `Sim101`, 60 barov predhistórie na cene 100.

**`engine`** — čo engine chce na `bar`-tom živom bare (1 = prvý):

| `action` | polia |
|---|---|
| `entry` | `id`, `type` (`limit` / `stop` / `market`), `dir` (1 / −1), `entry`, `sl`, `tp`, `qty`, voliteľne `trail_act` + `trail_off` (trailing v bodoch) |
| `cancel`, `close` | `id` |
| `close_session` | — (koniec seansy: všetko von) |

**`steps`** — čo sa deje vo svete:

| `do` | čo urobí |
|---|---|
| `bar` | uzavrie ďalší 1m bar (`o`, `h`, `l`, `c`; inak posledná cena) a posunie čas na jeho koniec |
| `advance` | `s` sekúnd, slučka inštancie každú sekundu |
| `fill` | vyplní živý order `order` (`qty`, `price`; `lose_exec: true` = order je Filled, ale správa o exekúcii nepríde) |
| `rule` | pravidlo poruchy, viď nižšie |
| `release` | doručí držané udalosti (`match` = len pre daný order) |
| `cancel_outside` | order zrušený mimo stratégie |
| `foreign` | cudzí trhový order na tom istom účte (`side`, `qty`, `name`) — Chart Trader Close |
| `disconnect` / `connect` / `positions` | stav spojenia; účet po výpadku pozície neukazuje (`hide_positions`, `positions: false`, `visible`) |
| `session` | `open: false` = mimo seansy (strážca feedu) |
| `control` | zapíše control súbor (`mode`: `enabled` / `paused` / `flatten`) |
| `crash` / `stop` / `start` | pád platformy (bez `Teardown`), riadne zastavenie, nový štart nad tým istým stavom |

**Pravidlo poruchy** — `on`: `submit` / `cancel` / `change`; `match`: meno orderu (`L1`, `L1:sl`,
`L1:tb_close`; `*` na konci = predpona); `times`: koľkokrát platí; `then`:

| `then` | broker |
|---|---|
| `reject` | požiadavku odmietne (pri `submit` order končí ako Rejected; pri `cancel` / `change` stojí ďalej) |
| `ignore` | neurobí nič a nič nepovie (stratená správa) |
| `hold` | zrušenie prijme, ale potvrdenie zdrží do `release` — okno, v ktorom sa order ešte môže vyplniť; pri `submit` trhový order nevyplní |
| `throw` | volanie API skončí výnimkou |

## Výpis

`trace` má záznam po štarte a po každom kroku:

| pole | význam |
|---|---|
| `position` | pozícia účtu u brokera |
| `working` | živé ordery u brokera (meno, strana, typ, objem, cena, stav) |
| `tracked`, `tracked_position` | čo sleduje inštancia (`_orders`) a aká pozícia z toho vychádza |
| `dying` | ordery, ktorých zrušenie broker ešte nepotvrdil a inštancia ich stráži |
| `held` | udalosti, ktoré broker drží |
| **`naked`** | pozícia u brokera bez stop orderu na celý objem a bez trhového výstupu na ceste |
| **`orphans`** | výstupné ordery (`id:…`) u brokera bez pozície |
| **`unknown`** | pozícia u brokera ≠ pozícia, ktorú si myslí inštancia |

K tomu `requests` (všetko, čo adaptér od brokera chcel, s výsledkom pravidla), `seen_position`
(pozícia, akú adaptér hlásil enginu na každom živom bare), `log` a `error`.

Krátke okno `naked` je niekedy správne — SL odmietnutý brokerom položí strážca znova až po 2 s, kým
platforma nebeží, pozíciu nestráži nikto. Test preto hovorí, **kde** okno smie byť a že na konci nie je.

## Model brokera — čo je predpoklad

Falošný broker je model, nie NinjaTrader. Overené voči NT je len to, čo adaptér už dnes naživo robí;
zvyšok sú predpoklady, ktoré treba mať na pamäti pri čítaní výsledku:

- Udalosti chodia v poradí `OrderUpdate` → `ExecutionUpdate`; stav orderu (`Order.OrderState`) sa mení
  v okamihu doručenia udalosti, nie požiadavky.
- OCO: vyplnený **alebo zrušený** order stiahne ostatné zo skupiny; odmietnutý nie.
- Odmietnuté zrušenie a odmietnutá zmena prídu ako `OrderUpdate` so stavom `Rejected`, ale order ostáva
  živý (pre zmenu to tak adaptér pozoroval naživo; pre zrušenie je to predpoklad).
- Trhový order sa vyplní hneď za poslednú cenu; limit a stop sa samy nevypĺňajú — výplň je vždy krok
  scenára (`fill`), aby bolo poradie udalostí v rukách testu.
- Výplň pre order, ktorý už je zrušený alebo odmietnutý, sa zahodí; zrušenie pre order, ktorý sa medzitým
  vyplnil, tiež.
- Pozícia účtu sa mení v okamihu exekúcie (NT ju hlási o chvíľu neskôr — to pokrýva `positions`).

Scenár, ktorý prejde tu, teda nenahrádza skúšku na Sim101; hovorí, že **stavový automat adaptéra** je
na dané poradie udalostí pripravený.

## Čo simulátor našiel (10. 11. 2026)

1. **SL/TP ostali u brokera po trhovom výstupe.** Keď sa zrušenie SL/TP pri zatváraní nepotvrdilo do
   10 s, trhový výstup šiel aj tak (správne), pozícia sa zavrela a inštancia obchod zabudla — SL a TP
   však stáli ďalej bez pozície. Stop bez pozície by neskôr otvoril obchod, o ktorom nikto nevie.
   Oprava: `Drop` výstupy zruší a stráži (`_dying`, `Exit`), kým to broker nepotvrdí; keby sa taký
   order predsa vyplnil, pozícia sa prevezme so zrkadlovým plánom a hneď zavrie trhom.
2. **Odmietnuté zrušenie vstupu sa bralo ako koniec orderu.** Inštancia order prestala strážiť, hoci
   stál ďalej; jeho výplň by bola pozícia bez SL. Oprava: rušený order sa zabudne až vtedy, keď naozaj
   nie je živý.
3. Zastavenie inštancie (`Teardown`) ruší čakajúce vstupy a na potvrdenie nečaká. Výplň, ktorá zrušenie
   predbehne, prevezme až ďalší štart (`RestoreState` ju nájde v exekúciách účtu). Nie je to chyba kódu,
   ale dôvod, prečo AddOn inštanciu po páde spúšťa znova — test to drží ako známe správanie.

## Ako pridať scenár

Test v `tester/tests/test_ninjatrader_faults.py`: `play(engine, steps)` vráti výpis a zlyhá, keď scenár
nedobehol; `assert_clean` / `assert_flat` overia posledný krok, `faultsim.naked_steps(out)` celú cestu.
Nový nález naživo = najprv scenár, ktorý ho ukáže, potom oprava.
