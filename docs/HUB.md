# Distribuované počítanie: hub a agenti

Backtesty a hyperopty sa dajú rozhodiť na viac strojov. Model je jednoduchý: jeden
**hub** s verejnou adresou, na ktorý sa hlásia **agenti** — každý klon repozitára, ktorý
má nastavený `tester/agent.json`. Agent môže výpočty **prijímať**, **posielať**, alebo
oboje. Kód je v `tester/hub/`, architektúra v docstringu
[`tester/hub/__init__.py`](../tester/hub/__init__.py).

```
                     hub (verejný, python -m tester.hub serve)
                     agenti · fronta · zipy výsledkov · stav na disku
                  ▲ heartbeat ~10 s        ▲ POST /api/jobs         ▲ zip
        ┌─────────┴──────┐        ┌─────────┴──────┐        ┌─────────┴──────┐
        │ srv-01         │        │ notebook       │        │ srv-02         │
        │ headless agent │        │ webapp, send   │        │ webapp, accept │
        │ accept, 16 j.  │        │ (zadáva)       │        │ + send         │
        └────────────────┘        └────────────────┘        └────────────────┘
```

## Prečo agent ťahá a hub netlačí

Servery aj notebooky sú za NAT-om; verejnú adresu má len hub. Agent sa preto hubu **hlási
sám** každých ~10 s (heartbeat) a v odpovedi dostane, čo mu hub pridelil, čo má zrušiť a
čo mu (ako zadávateľovi) dobehlo. Oneskorenie je najviac jeden interval, čo je pri behoch
na minúty jedno. Hub sám nič nepočíta a nič nevie o stratégiách — nesie `params` a
`settings` behu tak, ako ich prijíma `POST /api/runs` webapp.

## Mená, stav, výsledky

- **Meno agenta je statické a jednoznačné** (`--name` pri setupe). Podľa neho hub pozná
  agenta cez reštarty a výpadky siete a podľa neho vie, **komu vrátiť výsledok** — výpočet
  nesie meno zadávateľa. Druhý agent s tým istým menom je odmietnutý, kým prvý žije.
- **Hub má stav na disku** (`tester/hub_data/state.json`, zipy v `results/`). Po páde
  s výpočtami vo fronte sú po štarte stále tam; agenti sú offline, kým sa neohlásia.
- **Agent má stav na disku** (`tester/agent_state.json`): čo **poslal** a ešte sa
  nevrátilo, a čo **počíta** pre hub (hub výpočet → lokálny beh). Po reštarte v oboch
  pokračuje.
- **Výsledok je adresár behu.** Počítajúci agent beh spočíta do vlastnej histórie
  (`tester/runs/`), po dobehnutí adresár zabalí (u hyperoptu aj päť overovacích behov
  víťaza) a odovzdá hubu. Zadávateľ ho dostane vo svojom heartbeate, rozbalí do svojej
  histórie a potvrdí (`ack`) — hub zip zmaže. Beh potom u zadávateľa vyzerá presne tak,
  ako keby bežal lokálne: história webapp, `cli show`, Monte Carlo, všetko funguje.

## Kapacita: kto je voľný

Agent hlási počet jadier a **sloty** (koľko behov naraz; `max_parallel` v configu je
strop). Každý výpočet žiada `cores`:

| výpočet | žiada | prečo |
|---|---|---|
| backtest | 1 | Freqtrade s 1m detailom vyťaží jedno jadro |
| hyperopt | `all` (alebo `jobs`) | epochy idú cez joblib na všetky jadrá |
| beh s AI vrstvou | `all` | FreqAI trénuje na všetkých jadrách |

Backtest sa zmestí vedľa iných backtestov; hyperopt chce prázdny stroj a kým beží, nič
ďalšie na ten stroj nejde. Lokálna fronta agenta (čo si tester spustil sám vo webapp)
zaberá sloty rovnako. Pravidlá sú v [`tester/hub/protocol.py`](../tester/hub/protocol.py)
(`fits`, `eta_free`).

## Čas: kedy sa uvoľní

Agent pri každom heartbeate pošle **postup** a **odhad zvyšku** každého výpočtu:

- pred štartom z vlastnej histórie behov — medián sekúnd na deň okna (backtest) alebo
  sekúnd na epochu (hyperopt); bez histórie ~30 s na rok s 1m detailom,
- počas behu u hyperoptu z počtu hotových epoch (Freqtrade ich priebežne zapisuje do
  `.fthypt`; bez terminálu priebeh na obrazovku nevypisuje), po dobehnutí ladenia z
  overovacích behov víťaza (postup 80–100 %), u backtestu odpočtom od odhadu — po
  prekročení odhadu ostane malý zvyšok, nikdy nula.

Hub z toho vie pre každého agenta povedať, kedy by výpočet s danou požiadavkou zobral
(`eta_free_1`, `eta_free_all` v `status`), a pre nový výpočet **najskorší štart** aj
s tým, čo je vo fronte pred ním. To rozhoduje, či sa výpočet do fronty dá:

| zadanie | nikto voľný |
|---|---|
| `--remote` | odmietnuté s odhadom, kedy by sa dalo |
| `--remote --queue` | zaradené do fronty hubu |
| `--remote --queue --max-wait 30` | zaradené, len ak odhadované čakanie nepresiahne 30 min |

Odhad je plus mínus — je to medián z histórie toho stroja, nie meranie. Na rozhodnutie
„fronta, alebo nie" stačí.

## Verzia kódu

Rovnaký beh na inom commite dá iné čísla. Preto výpočet nesie **commit zadávateľa**
(`git rev-parse --short HEAD` v momente zadania; CLI upozorní, keď má zadávateľ
necommitnuté zmeny kódu — tie k agentovi nedôjdu). Počítajúci agent commit pred prijatím
overí (`git merge-base --is-ancestor`) a keď ho nemá:

1. počká, kým dobehne, čo práve počíta (pull uprostred behu nie),
2. spraví `git pull --rebase --autostash origin main` (to isté, čo Pull vo webapp),
3. overí znova — keď commit nie je ani po pulle (zadávateľ ho nepushol do `main`),
   výpočet zlyhá s chybou, ktorá to povie.

Po pulle je kód v bežiacom procese starý. **Headless agent sa reštartuje sám** (hub mu
po `bye` pridelený výpočet podrží a nový proces si ho vezme). **Webapp** to hlási
v `GET /api/hub` (`needs_restart`) a v `python -m tester.hub status`; samotný beh už ide
na novom kóde, lebo Freqtrade beží v podprocese — ale registry stratégií v procese webapp
je staré, takže ju treba reštartovať, ako po každom `git pull`.

Po pulle si agent **zloží nové dáta z archívu** (`data_archive merge`, dopočet timeframov)
— rovnaký commit tak znamená rovnaké páry aj timeframy u každého agenta.

Hub pri prideľovaní **uprednostní agenta, ktorý commit už má**, aby sa pullovalo čo
najmenej. Beh v histórii nesie `settings.hub` (výpočet, zadávateľ, agent, žiadaný a
skutočný commit) a hotový výpočet má `agent_version`; CLI upozorní, keď sa líši od
zadaného (agent stál na novšom `main`).

## Rušenie

Výpočet môže zrušiť **zadávateľ** (`cli`, alebo `python -m tester.hub cancel <id>`) aj
**hub** (to isté z hubového klonu). Vždy ide o tú istú cestu: hub označí výpočet
`cancelling`, v heartbeate to povie **počítajúcemu** agentovi (ten beh zabije, aj
overovacie behy víťaza, a odovzdá stav `cancelled`) a v heartbeate **zadávateľa** sa
výpočet objaví medzi hotovými so stavom `cancelled` a menom toho, kto ho zrušil. Výpočet
vo fronte sa zruší hneď.

Agent, ktorý sa prestane hlásiť (45 s), je offline: čo mu bolo pridelené a ešte
nebežalo, ide späť do fronty; čo bežalo, sa raz skúsi znova, ak výpočet frontu dovolil,
inak zlyhá s chybou „agent sa odmlčal". Beh, ktorý agent tri heartbeaty po sebe
nenahlási (reštart bez stavu), zlyhá tiež.

## Nastavenie

**Hub** (jeden stroj s verejnou adresou; TLS nech rieši reverse proxy):

```bash
TRADEBOT_HUB_TOKEN=dlhy-nahodny-retazec PY -m tester.hub serve --host 0.0.0.0 --port 8790
```

Na verejnej adrese je token povinný; každé volanie API ho nesie v hlavičke
`Authorization: Bearer …`. Bez tokenu hub beží len na `127.0.0.1`.

**Tokeny per agent.** Hlavný token (`TRADEBOT_HUB_TOKEN`) je správcovský a nepatrí na
servery. Každý agent dostane vlastný token, ktorý ho zároveň **identifikuje**:

```bash
PY -m tester.hub token add srv-01          # vypíše token — raz; potom je v tokens.json
PY -m tester.hub token list
PY -m tester.hub token rm srv-01
```

Príkaz ide cez API s tokenom z `tester/agent.json` (musí to byť hlavný), alebo
`--local` priamo nad `tester/hub_data/` na stroji hubu (v kontajneri `docker compose
exec hub …`); bežiaci hub si zmenu súboru všimne sám. S vlastným tokenom sa agent hlási
len pod svojím menom, zadáva len ako on, výsledky sťahuje len k svojim výpočtom a rušiť
smie len to, čo zadal alebo počíta; parametre cudzieho behu neuvidí. Prepínanie
`accept` z hubu a správa tokenov sú len pre správcu. Hub bez jediného tokenu (vývoj na
localhoste) je otvorený.

**Log udalostí.** Hub zapisuje každú udalosť do `tester/hub_data/events.jsonl` (riadok
na udalosť, rotuje pri 20 MB): `agent_online`, `agent_offline`, `agent_bye`,
`job_submitted`, `job_assigned`, `job_started`, `job_finished` (stav, agent, chyba,
behy), `job_cancel` (kto), `job_requeued`, `job_timeout`, `accept_request`,
`token_added`, `token_removed`.

```bash
PY -m tester.hub events                              # posledných 50
PY -m tester.hub events --job 8fc63a805c18           # jeden výpočet od zadania po výsledok
PY -m tester.hub events --agent srv-01 --event job_finished --limit 200
```

`GET /api/events?limit=&job=&agent=&event=` je to isté cez API (ktorýkoľvek platný token).

**Agent** (každý klon, ktorý má počítať alebo posielať):

```bash
PY -m tester.hub setup --name srv-01 --hub-url https://hub.example.com:8790 --token … --accept --send
PY -m tester.hub setup --name notebook --no-accept          # len zadáva
PY -m tester.hub setup --max-parallel 4                     # strop behov naraz
```

Zapíše `tester/agent.json` (gitignored; premenné `TRADEBOT_HUB_URL`, `TRADEBOT_HUB_TOKEN`,
`TRADEBOT_HUB_NAME`, `TRADEBOT_HUB_ACCEPT`, `TRADEBOT_HUB_SEND` ho prebijú — pre Docker).
Agent potrebuje to isté, čo každý klon: `.venv` zo setup skriptu a zložený sklad sviečok
(`PY -m tester.data_archive merge`; headless agent si ho zloží sám).

Agent beží dvoma spôsobmi:

| | príkaz | kedy |
|---|---|---|
| **webapp** | `./webapp.sh` (agent štartuje s ňou, keď `agent.json` existuje) | stroj, na ktorom niekto aj klikne |
| **headless** | `PY -m tester.hub agent` | server bez prehliadača |

## Docker

Dva samostatné compose súbory, oba sa spúšťajú z koreňa repozitára (Docker tu pri písaní
nebol k dispozícii — build nebol overený, súbory sú podľa `docker/docker-compose.yml`):

**Hub** — malý image bez Freqtradu (`docker/Dockerfile.hub`), stav vo volume `hub_data`:

```bash
cp .env.example .env         # TRADEBOT_HUB_TOKEN=… (povinný), TRADEBOT_HUB_BIND, TRADEBOT_HUB_PORT
docker compose -f docker/docker-compose.hub.yml up -d --build
docker compose -f docker/docker-compose.hub.yml exec hub python -m tester.hub token add srv-01 --local
docker compose -f docker/docker-compose.hub.yml exec hub python -m tester.hub events --local
```

Port sa predvolene viaže na `127.0.0.1` — pred hub patrí reverse proxy s TLS (Caddy,
nginx). `TRADEBOT_HUB_BIND=0.0.0.0` ho dá priamo na sieť, ale potom ide token po HTTP.

**Headless agent** — image `docker/Dockerfile.agent` stavia na image Freqtradu s jadrom
(`docker compose -f docker/docker-compose.yml build freqtrade` najprv) a pridáva git:

```bash
# .env: TRADEBOT_HUB_URL, TRADEBOT_HUB_TOKEN (token TOHTO agenta), TRADEBOT_HUB_NAME, TRADEBOT_HUB_MAX_PARALLEL
docker compose -f docker/docker-compose.agent.yml up -d --build
docker compose -f docker/docker-compose.agent.yml logs -f
```

Kontajner mountuje z hostiteľa `tester/` (história, stav agenta), `data/` a
`data_archive/` (sklad sviečok; chýbajúce si zloží pri štarte), `deploy/freqtrade/`,
`tradebot/` (read-only) a `.git/` (read-only, len na verziu). **`git pull` sa v kontajneri
nerobí** (`TRADEBOT_HUB_PULL=off`) — rob ho na hostiteľovi; agent zmenu kódu na disku
spozná, dočíta, čo počíta, odhlási sa a skončí, a `restart: unless-stopped` ho zdvihne na
novom kóde. Výpočet s commitom, ktorý hostiteľ ešte nepullol, zlyhá s chybou, ktorá to
povie. Push/Pull histórie behov sa robí z hostiteľa.

Webapp so zapnutým `accept` si nastaví toľko workerov, koľko má slotov — behy z hubu
bežia vedľa seba (každý má vlastný adresár výsledkov Freqtradu), hyperopt sám.

## Použitie

```bash
PY -m tester.hub status                                   # agenti, fronta, kedy sa kto uvoľní
PY -m tester.webapp.cli run --remote --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
    --timerange 20250904-20260904 --note "rok 2025-26 na serveri"
PY -m tester.webapp.cli hyperopt --remote --queue --max-wait 60 --param rrRatio=2:8:0.5 \
    --param slLookback=5:40:1 --timerange 20250904-20260904 --goal break_even --epochs 200 \
    --note "hyperopt na srv-01"
PY -m tester.hub jobs                                     # živé výpočty; --all aj hotové
PY -m tester.hub cancel <job_id>
```

`run --remote` sa najprv spýta na kapacitu, vypíše, kto je voľný a najskorší štart, pošle
výpočet, čaká (postup, zvyšok) a hotový beh rozbalí do lokálnej histórie — `cli show`,
webapp aj `hyperopts <id>` ho ukážu ako každý iný. Keď na notebooku beží webapp, zadanie
ide cez ňu (`POST /api/hub/jobs`): jej agent si zapíše, čo poslal, a výsledok vyzdvihne
sám, aj keď CLI medzitým zavrieš. `--no-wait` len zadá a skončí.

**Mriežky idú naraz.** `sweep`, `checkup`, `matrix` a `plateau` s `--remote` zadajú
všetky body hneď (fronta je pri mriežke vždy povolená, `--max-wait` platí), hub ich
rozdá na toľko agentov, koľko je voľných, a príkaz si ich vyzdvihuje v poradí — tabuľka
na konci je tá istá ako pri lokálnom behu. Po Ctrl+C výpočty na hube bežia ďalej
(`python -m tester.hub jobs`, `cancel <id>`).

```bash
PY -m tester.webapp.cli sweep --remote --param rrRatio=2:6:1 --profile … --timerange 20250904-20260904
PY -m tester.webapp.cli checkup --remote --strategy ibs --profile …      # päť okien na piatich agentoch
```

## Webapp

Keď má klon `tester/agent.json`, webapp ukáže kartu **Hub**: stav tohto agenta (online,
commit, prepínač **prijímať výpočty**, ktorý platí hneď a zapíše sa do configu), tabuľku
agentov (kto je online, koľko má voľné, kedy sa uvoľní) a výpočty na hube s postupom,
zvyškom a tlačidlom na zrušenie. Pri **Spustiť backtest** a pri hyperopte v „Hľadať
parametre" je prepínač **na hube** (s frontou a stropom čakania) — zadanie je to isté ako
lokálne, len ho spočíta voľný agent a výsledok sa objaví v histórii, keď si ho agent
webapp vyzdvihne.

## Prijímanie za behu, strop na čas, viac seedov

- **Prijímanie** sa dá prepnúť bez reštartu: v karte Hub, zmenou `tester/agent.json`
  (`python -m tester.hub setup --no-accept`, agent si súbor prečíta pri najbližšom
  heartbeate) alebo z hubu: `python -m tester.hub accept srv-01 off` — hub to agentovi
  povie v heartbeate a agent si to zapíše do configu.
- **Strop na čas behu.** Zaseknutý Freqtrade by držal výpočet v `running` donekonečna.
  Agent preto beh zabije po `--max-runtime MIN` (v CLI alebo cez API), inak po
  trojnásobku odhadu, najmenej 10 minút; výpočet skončí ako `failed` s chybou, ktorá
  strop uvedie. Hub je poistka: to isté vymáha o dva heartbeat intervaly neskôr.
- **Viac seedov.** `cli hyperopt --remote --seeds 3` pustí ten istý hyperopt s tromi
  seedmi (od `--seed` alebo 1) naraz na hube a na konci porovná víťazov: `ROVNAKE`, keď
  všetky skončili na tých istých hodnotách (optimum nie je náhoda jedného behu), `ROZNE`,
  keď nie (priestor je plochý alebo šum — presná hodnota nerozhoduje, over cez plateau).
  Je to náhrada za delenie hyperoptu medzi stroje, ktoré Freqtrade nedovolí.

## API hubu

Všetko pod `/api/`, s tokenom; `/api/health` bez neho.

| volanie | kto | čo |
|---|---|---|
| `POST /api/agents/register` | agent | meno, jadrá, sloty, `accept`, `send` |
| `POST /api/agents/{name}/heartbeat` | agent | stav výpočtov + lokálna záťaž → `assign`, `cancel`, `finished`, `set_accept` |
| `POST /api/agents/{name}/accept?value=` | správca | zapnúť/vypnúť prijímanie na agentovi |
| `GET /api/tokens`, `POST/DELETE /api/tokens/{name}` | správca | tokeny agentov |
| `GET /api/events` | ktokoľvek | log udalostí (`limit`, `job`, `agent`, `event`) |
| `GET /api/capacity?cores=1\|all` | zadávateľ | kto by zobral hneď, najskorší štart, fronta |
| `POST /api/jobs` | zadávateľ | `kind`, `payload{params,settings,note,user}`, `cores`, `queue`, `max_wait_seconds`, `estimate_seconds` → 409 s odhadom, keď nikto |
| `GET /api/jobs[/{id}]` | ktokoľvek | stav, postup, ETA, agent, zadávateľ |
| `POST /api/jobs/{id}/cancel` | zadávateľ / hub | `cancelling` → agent → `cancelled` |
| `POST /api/jobs/{id}/result` | počítajúci agent | zip histórie (`?status=done\|failed\|cancelled&run_ids=…`) |
| `GET /api/jobs/{id}/result` | zadávateľ | zip; 410, keď už bol vyzdvihnutý |
| `POST /api/jobs/{id}/ack` | zadávateľ | výsledok mám, zip zmaž |
| `GET /api/status`, `GET /api/agents` | ktokoľvek | prehľad |

Webapp k tomu pridáva `GET /api/hub` (stav jej agenta a hubu), `POST /api/hub/jobs`
(hotový payload z CLI), `POST /api/hub/runs` a `POST /api/hub/hyperopts` (zadanie
z formulára), `POST /api/hub/accept` (prepínač prijímania) a
`GET/POST /api/hub/jobs[/{id}[/cancel]]`.

## Čo hub nerobí

- Nedelí jeden hyperopt medzi viac strojov. Freqtrade drží Optuna štúdiu v pamäti procesu;
  zdieľané úložisko by bol zásah do jeho privátneho API. Namiesto toho sa dá pustiť
  ten istý hyperopt s rôznym `--seed` na rôznych agentoch — keď skončia na tom istom plató,
  je to silnejší signál než jedno hľadanie s viac epochami.
- Nesynchronizuje dáta. Každý agent musí mať zložený sklad sviečok (`data_archive
  merge`); kód si pullne sám (viď „Verzia kódu"), ale len to, čo je v `main`.
- Nerobí TLS ani používateľov — token per agent je identita, šifrovanie dá reverse proxy.
