# HTTP API webapp (Tester)

Všetko, čo robí stránka webapp, ide cez toto API — formulár, CLI (`python -m tester.webapp.cli …`, keď
webapp beží) aj skripty a AI volajú tie isté endpointy. Tento dokument je manuál: čo ktorý endpoint robí,
čo berie, čo vracia a kedy ho použiť. Presné schémy (každé pole s popisom) generuje FastAPI sám:

- **`http://127.0.0.1:8765/docs`** — interaktívny prehľad (Swagger UI), dá sa z neho rovno volať,
- **`http://127.0.0.1:8765/openapi.json`** — strojovo čitateľná schéma (pre generátor klienta alebo AI).

Webapp beží lokálne (`./webapp.sh`, `.\webapp.ps1`), bez prihlasovania; na port 8765 nemá prístup nikto
zvonka. Hub (distribuované počítanie) má vlastné API s tokenom — [HUB.md](HUB.md).

**Pravidlá pre všetky endpointy:**

- telo aj odpoveď sú JSON; čas je ISO 8601 UTC, obdobie `YYYYMMDD-YYYYMMDD` (koniec nepatrí dnu);
- chyba zadania = **422** s vetou v `detail`, ktorá hovorí, čo je zle (napr. „pre NAS100/USD nie sú
  stiahnuté 1m dáta"); 404 = taký beh / hyperopt nie je;
- poplatok `fee` je **podiel** na stranu (0,0005 = 0,05 %); bez neho sa vezme náklad trhu (`fee_note`);
- `params` sú **celé parametre** stratégie ako vo formulári — tie beh naozaj použije. `profile` je pri behu
  len popis (odkiaľ parametre sú); parametre profilu dá `GET /api/profiles/<meno>?strategy=<kľúč>&engine=<engine>`
  → `params`. `params: {}` = Pine defaulty stratégie. (Výnimka: `/api/native/backtests` profil načíta sám.)
- každý beh nesie `note` — bez poznámky je história na nič.

---

## 1. Čo je na výber

| | |
|---|---|
| `GET /api/meta` | stratégie, páry (s rozsahom dát, TF a burzou), referenčné okná, enginy |
| `GET /api/strategies/{key}/meta` | parametre stratégie (popisy, skupiny, rozsahy, defaulty), profily |
| `GET /api/profiles?strategy=` · `GET /api/profiles/{meno}` | profily (repozitár aj vlastné testera) |
| `GET /api/hyperopt/meta?strategy=` | odporúčaný priestor, varovania, okná, `native` (má C# jadro), `samplers` |
| `GET /api/native/status` | pracovné procesy C# (strop, požičané, voľné), stratégie, ktoré vedia bežať natívne |

## 2. Jeden beh

| | |
|---|---|
| `POST /api/runs` | zaradí backtest do fronty; odpoveď `{"id": …}` |
| `GET /api/queue` | fronta: čo čaká, čo beží (s priebehom) |
| `POST /api/queue/{id}/cancel` | zruší beh alebo hyperopt: čakajúci hneď, bežiaci zabitím podprocesu; natívny beh (C# bod, natívny hyperopt) podproces nemá — dobehne a výsledok sa zahodí |
| `GET /api/runs?q=&limit=&offset=` | história (hľadanie `q` ako v karte História) |
| `GET /api/runs/{id}` | detail: `settings`, `params`, `result` (súhrn), `series` |
| `GET /api/runs/{id}/log` · `/montecarlo` · `/chart` · `/profile.json` | log, Monte Carlo, kresby, profil behu |

Telo `POST /api/runs` (rovnaké polia berú aj sweep, matica a hyperopt):

```json
{"strategy": "orbnet", "pair": "NAS100/USD", "engine": "multicharts", "timeframe": "3m",
 "timerange": "20240904-20250904", "fee": 0.0001, "wallet": 10000, "timeframe_detail": "1m",
 "profile": "nas100_dukascopy_3m", "params": {…}, "note": "ORB: RR 2", "user": "materko"}
```

`engine`: `freqtrade` (krypto fill model, Freqtrade) alebo `multicharts` (emulátor MultiCharts — fill model
NT8/MT5); bez neho podľa dát. Na emulátore beží **obyčajný beh** Python emulátorom (s kresbami do grafu);
body celkov (nižšie) C# stratégií počíta natívne C#.

## 3. Viac behov naraz

| | |
|---|---|
| `POST /api/sweeps` | mriežka: telo behu + `space` (`{"rrRatio": "1:4:0.5"}`), `goal`, `max_dd`, `min_trades` |
| `GET /api/sweeps?strategy=` · `GET /api/sweeps/{id}` · `POST /api/sweeps/{id}/cancel` | mriežky a ich tabuľka |
| `POST /api/matrices` · `GET /api/matrices/{id}` | ten istý profil na viacerých trhoch a TF (`pairs`, `timeframes`) |
| `POST /api/points/{id}/replay` | bod mriežky / matice / overenia prehrá ako obyčajný beh do histórie |
| `POST /api/analytics/prepare` · `GET /api/analytics` | základná analytika (päť okien, test proti náhode, …) |

**Body celkov C# stratégií na emulátore MultiCharts** (sweep, matica, okolie víťaza, overenie hyperoptu) počíta
pracovný proces C# (`tester.native`) — súhrn, obchody aj séria sú tie isté ako z Python emulátora
(`tester/tests/test_native_modes.py`), len rádovo rýchlejšie. `TRADEBOT_NATIVE_BATCH=0` to vypne.

## 4. Hyperopt

| | |
|---|---|
| `POST /api/hyperopts` | zaradí hyperopt; odpoveď `{"id", "epochs", "goal_note", "native", "warn", "knobs"}` |
| `GET /api/hyperopts?strategy=` | hyperopty z histórie |
| `GET /api/hyperopts/{id}` | detail: stav, priebeh, epochy, víťaz, overenie, verdikt |
| `POST /api/hyperopts/{id}/continue` | ďalšie epochy (`{"epochs": 200}`) — nový záznam so starými aj novými (Freqtrade: zlúčenie) |
| `POST /api/hyperopts/{id}/plateau` | zaradí susedov víťaza (±1 a ±2 kroky) — plató, alebo špička? |
| `POST /api/hub/hyperopts` | to isté zadanie na hub (+ `cores`, `queue`, `max_wait_minutes`, …) |

Telo `POST /api/hyperopts` = telo behu a k nemu:

| pole | | |
|---|---|---|
| `space` | povinné | `{"rrRatio": "0.75:4:0.25", "tradeDirection": "Both,Long only"}` — rozsah alebo možnosti |
| `goal` | `break_even` | `break_even` · `profit` · `winrate` · `drawdown` |
| `max_dd`, `min_trades` | — | mantinely: strop drawdownu v %, minimum obchodov **za rok** |
| `epochs`, `seed`, `verify` | 200, —, true | koľko epoch; seed sampleru; víťaz na piatich oknách |
| `sampler` | — | `tpe` · `cmaes` · `nsga2` · `nsga3` · `qmc` · `random`; bez neho natívne TPE, Freqtrade NSGA-III |
| `windows` | — | okná kritéria `["20221001-20231001", …]` — skóre sa počíta na každom okne zvlášť |
| `aggregate` | `min` | `min` (najhoršie okno) · `median` · `mean` |
| `objectives` | — | ďalšie ciele `["drawdown", "trades"]` → Pareto hranica |
| `select` | `best` | `plateau` = víťaz s najlepším okolím, nie ostrá špička |
| `mode` | `search` | `walkforward` = ladí na okne N, meria na N+1 (okná z `windows`, inak päť) |
| `anchored` | false | walk-forward: ladiť na všetkých oknách do N |
| `continue_from` | — | id hyperoptu, ktorého epochy pokračovanie prevezme (to isté robí `/continue`) |

Rozšírenia (`windows` až `continue_from`) vedia **oba enginy**, líši sa cena a v dvoch prípadoch aj význam:

| | natívne (`engine: "multicharts"`, stratégia s C# jadrom) | Freqtrade |
|---|---|---|
| okná | epocha = samostatný beh na každom okne | **jeden beh cez rozpätie okien**, loss obchody rozdelí podľa otvorenia a každé okno hodnotí zvlášť (epocha trvá ako celé rozpätie; stav stratégie prechádza cez hranice okien) |
| viac cieľov | Optuna hľadá naraz vo všetkých (NSGA-II/TPE; nie CMA-ES) | hľadá sa podľa kritéria, **Pareto sa vyráta z metrík epoch** (drawdown, obchody, winrate, zisk — break-even ako ďalší cieľ nie) |
| okolie, walk-forward | C# dávky, sekundy | Freqtrade backtesty a hyperopty — minúty až hodiny (odhad v karte Hub) |
| pokračovanie | staré epochy sa **vložia do hľadania** | nový beh s iným seedom a **zlúčenie epoch** — optimalizátor sa zo starých neučí |

Natívne = `ibsnet`, `orbnet`, `ibsentrynet`, `vwaporbnet`, `vwapadxnet`, `noanet`, `tksnet` a `…eod`.

Detail `GET /api/hyperopts/{id}`:

```json
{"status": "running",
 "progress": {"done": 144, "total": 600, "elapsed_s": 9, "eta_s": 23, "s_per_epoch": 0.05},
 "hyperopt": {"knobs": {…}, "goal": "break_even", "native": true, "sampler": "tpe", "windows": [...],
              "epochs_done": 600, "distinct": 2840, "best": {…}, "overrides": {"rrRatio": 1.5, …},
              "pareto": [3, 17, …], "plateau_select": {"chosen": 42, "candidates": [...]},
              "walk_forward": {"folds": [{"train": [...], "test": "…", "params": {…}, "result": {…}, "edge": 0.03}],
                               "verdict": "WALK-FORWARD NEJASNE: …"}},
 "epochs": [{"epoch": 42, "loss": -0.031, "params": {"hp_rrRatio": 1.5}, "trades": 812, "windows": {…},
             "values": [-0.031, 12.4], "pareto": true, "usable": true, "is_best": true}, …],
 "overrides": {…}, "verify": [{"timerange": "…", "tuned": true, "status": "done", "result": {…}}],
 "verdict": "VITAZ PREZIL: …", "plateau": null}
```

- `loss` je „menej je lepšie", **skóre = −loss**; `loss` ≥ 1000 = epocha mimo mantinelov (nie výsledok).
- `overrides` sú parametre víťaza v tvare pre `params` / `--set` — dajú sa rovno pustiť ako beh.
- `verdict`: `VITAZ PREZIL` / `NEJASNE` / `PRETRENOVANE` podľa znamienka break-even nad poplatkom v oknách
  mimo ladených. Walk-forward má verdikt vo `walk_forward.verdict` (`DRZI` / `NEJASNE` / `NEDRZI`).
- Priebeh `progress` je aj v `GET /api/queue`; na hube ho agent posiela v heartbeate.

## 5. Natívne behy bez histórie

`POST /api/native/backtests` — body × okná naraz na pracovných procesoch C#, výsledok hneď v odpovedi,
**nič sa neukladá**. Na prieskum, vlastný postup (napr. AI, ktorá skúša hypotézy) a overenie mimo histórie.

```json
{"strategy": "orbnet", "pair": "NAS100/USD", "timeframe": "3m", "profile": "nas100_dukascopy_3m",
 "windows": ["20231001-20241001", "20240904-20250904"], "fee": 0.0001, "wallet": 10000,
 "points": [{"rrRatio": 1.0}, {"rrRatio": 2.0, "nyRangeMinutes": 30}], "trades": false}
```

Odpoveď: `{"runs": 4, "seconds": 0.4, "fee": 0.0001, "windows": [...], "results": [{"point": 0, "values":
{"rrRatio": 1.0}, "window": "20231001-20241001", "summary": {"trades": …, "pnl_pct": …, "winrate": …,
"max_drawdown_pct": …, "break_even_pct": …, "profit_factor": …, …}}, …]}` — `summary` má tie isté kľúče a
čísla ako `result` behu v histórii. `params` (celé) prebijú profil, `points` sú zmeny k nim; `[{}]` = len
základ. Najviac 20 000 behov na dávku; s `trades: true` aj obchody každého behu (ako `trades.json`).

## 6. Ostatné oblasti

Polia a odpovede sú v `/docs`; tu je, na čo ktorá skupina je.

| | |
|---|---|
| `GET/POST /api/analytics/history` · `GET/DELETE /api/analytics/history/{id}` | uložené analytiky (záver s odkazmi na behy, nie obchody) |
| `POST /api/analytics/history/{id}/note` · `GET …/{id}/zadanie` · `POST …/{id}/posudok` | poznámka, čísla s otázkami pre AI, zápis posudku |
| `GET /api/diversify/trades` · `/live` · `/livedata` · `/livedata/view` | Diverzifikácia: obchody behov, inštancie naživo, živé behy z `data/live` |
| `GET /api/git/status` · `POST /api/git/pull` · `POST /api/git/push` | Pull a Push z hlavičky (Push len `runs/`, `sweeps/`, `profiles/`, `analytics/`, `archive/`) |
| `GET /api/hub` · `POST/DELETE /api/hub/config` · `POST /api/hub/token` | stav hubu a agentov, pripojenie webapp k hubu |
| `POST /api/hub/jobs` · `/runs` · `/hyperopts` · `GET /api/hub/jobs[/{id}]` · `POST …/{id}/cancel` | zadania na hub ([HUB.md](HUB.md)) |
| `POST /api/hub/accept` · `DELETE /api/hub/undelivered` · `POST/DELETE /api/hub/agents/{meno}[/update]` | prijímanie výpočtov, nedoručené výsledky, aktualizácia a odobratie agenta |
| `GET /api/live` · `/api/live/stream` (SSE) · `/api/live/{inst}/sessions` · `/snapshot` · `/lost` · `/events` | karta Live: telemetria inštancií ([LIVE.md](LIVE.md)) |
| `GET/POST/PATCH/DELETE /api/live/accounts` · `/api/live/deployments` · `GET /api/live/audit` | účty, nasadenia a ich záznam zmien |
| `GET /api/live/agents` · `POST/DELETE /api/live/agents/{meno}/update` · `GET /api/live/profiles` · `/deploy-defaults` | obchodné stroje, aktualizácia ich kódu, profily na nasadenie |
| `GET /api/prop/meta` · `POST /api/prop` | prop výzva: obchody behov cez pravidlá výzvy |
| `POST /api/paper` | zapíše meranie do `docs/merania/` z behov (to isté ako `cli paper`) |
| `GET /api/ai/meta` | predvolené hodnoty AI vrstvy a čo stratégia dovolí meniť |

## 7. Príklady

```bash
# päť okien jedného nastavenia, bez histórie
curl -s -X POST http://127.0.0.1:8765/api/native/backtests -H "Content-Type: application/json" \
  -d '{"strategy":"tksnet","pair":"MNQ/USD","points":[{"rrRatio":1.5}]}'

# natívny hyperopt cez štyri okná, víťaz podľa okolia
curl -s -X POST http://127.0.0.1:8765/api/hyperopts -H "Content-Type: application/json" -d '{
  "strategy":"orbnet","pair":"NAS100/USD","engine":"multicharts","timeframe":"3m","timerange":"20240904-20250904",
  "params":{}, "space":{"rrRatio":"0.75:4:0.25","nyRangeMinutes":"5:60:5"},
  "windows":["20211001-20221001","20221001-20231001","20231001-20241001","20240904-20250904"],
  "aggregate":"min","select":"plateau","epochs":400,"note":"ORB: robustne RR a range"}'
```

```python
import json, time, urllib.request

def api(path, body=None):
    req = urllib.request.Request("http://127.0.0.1:8765" + path, method="POST" if body is not None else "GET",
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))

job = api("/api/hyperopts", {"strategy": "tksnet", "pair": "MNQ/USD", "engine": "multicharts", "timeframe": "3m",
                             "timerange": "20240904-20250904", "params": {}, "space": {"rrRatio": "0.5:2:0.25"},
                             "mode": "walkforward", "epochs": 200, "note": "TKS walk-forward"})
while (d := api(f"/api/hyperopts/{job['id']}"))["status"] in ("queued", "running"):
    p = d.get("progress") or {}
    print(p.get("done"), "/", p.get("total"), "eta", p.get("eta_s"))
    time.sleep(3)
print(d["hyperopt"]["walk_forward"]["verdict"])
```

`params: {}` znamená „Pine defaulty stratégie". S profilom: `params = api(f"/api/profiles/{meno}?strategy=…&engine=multicharts")["params"]`
a k nemu `"profile": meno` (popis do histórie) — presne to robí formulár. CLI to robí samo (`--profile`): `python -m tester.webapp.cli hyperopt … --engine multicharts
--windows ref --select plateau` ([tester/AI_TESTING.md §8](../tester/AI_TESTING.md)).
