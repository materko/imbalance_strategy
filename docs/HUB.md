# Distribuované počítanie: hub a agenti

Backtesty a hyperopty sa dajú rozhodiť na viac strojov. Model je jednoduchý: jeden
**hub** s verejnou adresou, na ktorý sa hlásia **agenti** — každý klon repozitára, ktorý
má nastavený `tester/agent.json`. Agent môže výpočty **prijímať**, **posielať**, alebo
oboje. Kód je v `tester/hub/`, architektúra v docstringu
[`tester/hub/__init__.py`](../tester/hub/__init__.py).

```
                     hub (verejný, python -m tester.hub serve)
                     agenti · fronta · zipy výsledkov · stav na disku
                  ▲ heartbeat ~3 s         ▲ POST /api/jobs         ▲ zip
        ┌─────────┴──────┐        ┌─────────┴──────┐        ┌─────────┴──────┐
        │ srv-01         │        │ notebook       │        │ srv-02         │
        │ headless agent │        │ webapp, send   │        │ webapp, accept │
        │ accept, 16 j.  │        │ (zadáva)       │        │ + send         │
        └────────────────┘        └────────────────┘        └────────────────┘
```

## Štatistika agentov

Pod tabuľkou agentov ukazuje karta Hub, koľko výpočtov z hubu každý agent spravil
(behy, hyperopty) a ich priemerný čas, spolu a za posledných 24 h (kĺzavo). Hub ich ráta
pri odovzdaní výsledku (`tester/hub/stats.py`) a drží v zázname agenta v `state.json`,
lebo hotové výpočty sa zo zoznamu zahadzujú. Čas je od prvého hlásenia „running“ po
odovzdanie výsledku; zlyhané sa do priemeru nerátajú (počet je v tooltipe). Hub zo
staršieho kódu po aktualizácii započíta, čo z hotových výpočtov ešte drží.

## Druhy agentov

Na hube sú tri druhy strojov. Rozlišuje ich **rola** v `tester/agent.json` (`role`) a to,
**z čoho agent beží** (webapp alebo headless); stav hubu (`tester.hub status`, karta Hub) ich
ukazuje v stĺpci *druh*.

| druh | príklad | rola | beží ako | počíta pre hub | posiela | NT8 / MT5 |
|---|---|---|---|---|---|---|
| **webapp** | NB-rasto, MACMINIMARTIN | `compute` | `./webapp.sh` | keď má zapnuté *prijímať* | áno | nie |
| **počítací** | srvnas | `compute` | `PY -m tester.hub agent` | áno | zvyčajne nie | nie |
| **live** (obchodný) | nas-win11 | `live` | `PY -m tester.hub agent` (`deploy/agent`) | **nikdy** | áno (telemetria) | áno |

**Obchodný stroj nepočíta nikdy.** Backtesty by ho zahltili a NinjaTrader či MT5 by potom
nestíhali stratégie. Preto:

- rola `live` drží `accept` vždy na `false` — `setup --role live --accept` odmietne, prostredie
  (`TRADEBOT_HUB_ACCEPT`) ho nezapne, prepínač v karte Hub je zamknutý,
- hub stroj s rolou `live` **alebo s akýmkoľvek live nasadením** (aj pozastaveným) berie ako
  obchodný: nič mu nepridelí, `tester.hub accept <stroj> on` odmietne (409), a keď taký stroj
  predsa hlási `accept` (starý kód, config bez role), hub ho vypne u seba aj na stroji —
  v heartbeate mu pošle `set_accept: false` a agent si to zapíše do `agent.json`
  (udalosť `accept_forced_off`),
- pridelený a ešte nevzatý výpočet agenta, ktorý neprijíma, hub vráti do fronty
  (`job_requeued`); rozbehnutý výpočet nechá dobehnúť.

Rola sa nastaví pri inštalácii (`deploy/agent/README.md`): `PY -m tester.hub setup … --role live`.
Starý `agent.json` bez role je `compute`.

## Prečo agent ťahá a hub netlačí

Servery aj notebooky sú za NAT-om; verejnú adresu má len hub. Agent sa preto hubu **hlási
sám** každé ~3 s (heartbeat; interval určuje hub, `--heartbeat`, a agent si ho z odpovede prevezme) a v odpovedi dostane, čo mu hub pridelil, čo má zrušiť a
čo mu (ako zadávateľovi) dobehlo. Oneskorenie je najviac jeden interval, čo je pri behoch
na minúty jedno. Hub sám nič nepočíta a nič nevie o stratégiách — nesie `params` a
`settings` behu tak, ako ich prijíma `POST /api/runs` webapp.

## Mená, stav, výsledky

- **Meno agenta je statické a jednoznačné** (`--name` pri setupe). Podľa neho hub pozná
  agenta cez reštarty a výpadky siete a podľa neho vie, **komu vrátiť výsledok** — výpočet
  nesie meno zadávateľa. Druhý agent s tým istým menom je odmietnutý, kým prvý žije.
- **Premenovaný agent** ostane na hube pod starým menom ako offline (hub nevie, že je to
  ten istý stroj). Vyhodí sa ✕ v tabuľke agentov na karte **Hub**, alebo
  `python -m tester.hub forget <staré-meno> --with-token` (`--local` na stroji hubu,
  `--force`, keď ešte beží). Čo agent počítal, ide späť do fronty alebo zlyhá ako pri
  odmlčaní; token mu ostáva, pokiaľ sa nepýta aj oň.
- **Hub má stav na disku** (`tester/hub_data/state.json`, zipy v `results/`). Po páde
  s výpočtami vo fronte sú po štarte stále tam; agenti sú offline, kým sa neohlásia.
- **Agent má stav na disku** (`tester/agent_state.json`): čo **poslal** a ešte sa
  nevrátilo, čo **počíta** pre hub (hub výpočet → lokálny beh) a čo spočítal, ale nemal
  komu odovzdať (`undelivered`). Po reštarte vo všetkom pokračuje.
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
| hyperopt | `all` (alebo `jobs`) | epochy idú cez joblib na všetky jadrá; na emulátore MultiCharts (C# stratégie) ich počíta C# na vláknach (`tester.native_hyperopt`) |
| beh s AI vrstvou | `all` | FreqAI trénuje na všetkých jadrách |

Backtest sa zmestí vedľa iných backtestov; hyperopt chce prázdny stroj a kým beží, nič
ďalšie na ten stroj nejde. Lokálna fronta agenta (čo si tester spustil sám vo webapp)
zaberá sloty rovnako. Pravidlá sú v [`tester/hub/protocol.py`](../tester/hub/protocol.py)
(`fits`, `eta_free`).

## Čas: kedy sa uvoľní

Agent pri každom heartbeate pošle **postup** a **odhad zvyšku** každého výpočtu:

- pred štartom z vlastnej histórie behov — medián sekúnd na deň okna (backtest) alebo
  sekúnd na epochu (hyperopt); bez histórie ~30 s na rok s 1m detailom (natívny hyperopt
  na emulátore MultiCharts ~0,6 s na rok a jadro, s vlastnou históriou oddelenou od Freqtradu),
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

Sám od seba agent ťahá kód **len pre výpočet**, ktorého commit nemá. Aktualizovať ho dá aj
správca: tlačidlo **⟳** pri agentovi na karte Hub (alebo **⟳ aktualizovať všetkých** =
online počítajúci), `POST /api/agents/{meno}/update` s hlavným tokenom. Hub mu odvtedy nič
nepridelí (`update_request`), agent dopočíta, čo beží, spraví `git pull` (+ dáta) a vybavenie
nahlási v heartbeate (`pull_done` → `pull_result`, pri chybe čip „pull zlyhal"); headless
sa potom reštartuje sám, webapp sama, keď sa kód v gite zmenil (`TRADEBOT_AUTO_RESTART`).
Obchodný stroj (rola `live`) nie — ten má „Nový kód na stroji". Docker agent s
`TRADEBOT_HUB_PULL=off` nahlási, že pull treba spraviť na hostiteľovi; s `TRADEBOT_HUB_PULL=host`
pošle pokyn hostiteľovi (`tester/hub_pull_request`), ten hneď pullne a agent nahlási jeho
výsledok (viď „Headless agent" nižšie).

Po pulle si agent **zloží nové dáta z archívu** (`data_archive merge`, dopočet timeframov)
— rovnaký commit tak znamená rovnaké páry aj timeframy u každého agenta.

Hub pri prideľovaní **uprednostní agenta, ktorý commit už má**, aby sa pullovalo čo
najmenej. Beh v histórii nesie `settings.hub` (výpočet, zadávateľ, agent, žiadaný a
skutočný commit) a hotový výpočet má `agent_version`; CLI upozorní, keď sa líši od
zadaného (agent stál na novšom `main`).

## Behy spočítané pre iných

Agent počíta vo vlastnom runneri, takže beh vznikne aj v **jeho** `tester/runs/` — s tým
istým id, s akým ho hub vráti zadávateľovi. Keď ho zadávateľ commitne a pushne, `git pull`
na stroji agenta spadne (*untracked working tree files would be overwritten by merge*),
lebo ten istý súbor tam leží mimo gitu. Agent preto po **úspešnom odovzdaní** svoju kópiu
presunie do `tester/hub_delivered/` (gitignored; bod mriežky či overenia víťaza vyberie zo
`sweeps/` do `hub_delivered/points/`) a po 14 dňoch ju zmaže (`TRADEBOT_HUB_DELIVERED_DAYS`).
Beh patrí zadávateľovi a ten ho už má.

V histórii agenta ostáva výpočet, ktorý si zadal sám, a výpočet, ktorý hub neprijal
(`undelivered`). Behy spred tejto zmeny agent odloží raz po štarte — len tie, ktoré git
nesleduje (`tester/hub/delivered.py`).

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
nenahlási (reštart bez stavu), zlyhá tiež. To je ale len pohľad hubu — agent medzitým
počíta ďalej, viď nižšie.

Agent, ktorý sa reštartoval uprostred výpočtu (reboot stroja), beh v novom runneri nemá a `run.json`
ešte nevznikol: výpočet hubu neodovzdá ako `failed`, ale ho zabudne — hub ho podľa heartbeatu vráti do
fronty (raz, ak to fronta dovolila) a ten istý agent ho prijme znova. Heartbeat s iným `instance`, kým
pôvodný proces žije, hub odmietne (409) ako registráciu — dva procesy s jedným menom by dostali ten istý
výpočet. Výpočet vrátený do fronty preto, že agent prestal prijímať (`accept: false`), si agenta pamätá
v `lost_agents` a jeho neskorý výsledok prijme. Keď hub nevie zapísať `state.json` (plný disk), beží
ďalej z pamäti, ale chyba je v `/api/status` (`persist_error`), v udalostiach (`state_save_failed`)
a na karte Hub (audit 25. 10. 2026, N-HUB-1 až 4).

**Agent preto beží na dvoch vláknach.** Heartbeat musí odísť každé 3 sekundy (predvolený interval; hub môže poslať iný), ale zip
s výsledkom, jeho stiahnutie a hlavne `git pull` s poskladaním dát po ňom trvajú aj
minúty. Keby boli v jednom vlákne, hub by agenta uprostred tej práce vyhlásil za mŕtveho
a jeho výpočty rozdal ďalej — a keďže pull sa púšťa až vtedy, keď agentovi dobehnú behy,
vyzeralo by to, že agent ide offline zakaždým, keď niečo dopočíta. Pomalú prácu robí
`HubAgent.work()` vo vlastnom vlákne; kým sa ťahá kód, agent hlási `updating` a hub mu
dovtedy nič nové nepridelí (v tabuľke agentov je z toho chip „ťahá kód").

## Keď hub spadne

**Výpočet, ktorý už agent prijal, dopočíta aj bez hubu.** Lokálny runner o hube nevie:
beh ide do `tester/runs/` toho agenta rovnako, ako keby si ho tam pustil sám. Platí to aj
pre agenta, ktorým je **webapp** — hub je pre ňu len ďalší zadávateľ. Hub treba až na
odovzdanie výsledku.

Čo sa stane s výsledkom:

1. Kým sa výsledok neodovzdá, **záznam ostáva v `computing`** a agent to skúša pri každom
   ticku (~3 s), donekonečna, aj po reštarte agenta. Vo webapp to na karte **Hub** vidno
   ako „spočítané, čaká na hub N", v headless agentovi ako `caka na hub N`.
2. Keď hub vstane, výsledok odíde **hneď v prvom ticku** — ešte pred registráciou a
   heartbeatom (aby ho neblokovalo ani obsadené meno). Zlyhanie jedného odovzdania
   nepreruší tick: ostatné výpočty aj heartbeat idú ďalej.
3. Keď hub medzitým výpočet **odpísal** („agent sa odmlčal") alebo ho dal inému agentovi,
   hotový výsledok aj tak prijme: prepíše ním zlyhanie a zadávateľ ho dostane v svojom
   heartbeate (`late: true` na výpočte, udalosť `job_late_result`). Platí **prvý hotový** —
   keď to medzitým dopočítal niekto iný, neskorý výsledok sa zahodí a agentovi hub povie,
   nech beh zastaví.
4. Keď sa agent vráti skôr, než výpočet niekto prevezme, hub mu ho **vráti** (udalosť
   `job_readopted`) — nepočíta sa dvakrát.
5. Jediný prípad, keď výsledok naozaj nemá kam ísť, je hub, ktorý o výpočte nevie vôbec
   (stratený `state.json`). Po piatich pokusoch ide záznam do `undelivered` v
   `tester/agent_state.json` (webapp to hlási ako „neodovzdané N") — **behy ostávajú
   v histórii agenta**, len sa nevrátili zadávateľovi; dajú sa poslať cez GitHub ako
   ktorýkoľvek iný beh.
   Výpočet, ktorý hub vybavil inde a zo zoznamu už zahodil (`KEEP_FINISHED`), si pamätá
   (`forgotten`, posledných `KEEP_FORGOTTEN`) a neskorý výsledok naň dostane **410** — agent
   ho potichu odloží ako odovzdaný, do `undelivered` nejde. Staré hlásenie „Hub neprijal …"
   sa na karte Hub zavrie tlačidlom **✕ zabudnúť** (behy ostanú v histórii).
   Zo zoznamu hub zahadzuje vyzdvihnuté výpočty nad posledných `KEEP_FINISHED` a aj
   **nevyzdvihnuté bez výsledku** (zlyhané, zrušené) staršie než `STALE_UNCOLLECTED` (24 h);
   CLI `--remote` potvrdzuje (`ack`) aj zlyhaný výpočet. Tisíce nevybavených by hub
   spomalili — stav sa ukladá pri každom heartbeate.

Naopak, **hub bez agentov** nepotrebuje nič: má stav na disku, takže po reštarte sú
výpočty vo fronte stále tam a agenti sa prihlásia sami. Preto si hub v Dockeri dovolí
reštartovať sa aj sám, keď si stiahne nový kód (viď „Hub sa aktualizuje sám").

Po štarte má hub všetkých agentov zo `state.json` offline, kým sa neohlásia. Agent, ktorý
sa **do 45 s od štartu hubu neohlási**, sa berie ako odmlčaný: jeho výpočty idú späť do
fronty (ak ju dovolili), inak zlyhajú — a keď sa predsa vráti s hotovým behom, platí
bod 3 a 4 vyššie. Zadávateľ z CLI (`cli run --remote`) výpadok hubu prečká: čaká ďalej
s hláškou „hub nedostupny" a pokračuje, keď hub vstane.

### Ručný reštart hubu (upgrade)

Hub sa dá zhodiť kedykoľvek — nič sa nestratí (viď vyššie). Aby sa ale nič nerozpočítalo
zbytočne a fronta sa rozdelila až na novom kóde, pred ručným upgradom ho **vyprázdni**:

```bash
python -m tester.hub drain --wait     # nové výpočty len do fronty, počkaj, kým bežiace dobehnú
python -m tester.hub drain --stop     # … a potom hub skonči sám (Docker ho zdvihne na najnovšom kóde)
python -m tester.hub drain --off      # zrušiť, hub zas prideľuje
```

Drain je to isté, čo robí samoaktualizácia pri novom kóde (nižšie): hub nič nové
z fronty nepridelí, zadania bez `--queue` odmietne a `status` ukáže `DRAIN … dobieha N`.
Na disk sa nepíše — hub po reštarte zas prideľuje. Treba hlavný token: `admin_token`
z `tester/agent.json`, inak token agenta; na stroji hubu `--local` (127.0.0.1 a
`TRADEBOT_HUB_TOKEN`), v kontajneri `docker compose exec hub python -m tester.hub drain
--stop --local`. Pri `--stop`
hub skončí, keď nič nepočíta, a `hub-entrypoint.sh` si pri štarte stiahne najnovší kód,
takže je to ručný upgrade jedným príkazom.

## Nastavenie

**Hub** (jeden stroj s verejnou adresou; TLS nech rieši reverse proxy):

```bash
TRADEBOT_HUB_TOKEN=dlhy-nahodny-retazec PY -m tester.hub serve --host 0.0.0.0 --port 8790
```

Na verejnej adrese je token povinný; každé volanie API ho nesie v hlavičke
`Authorization: Bearer …`. Bez tokenu hub beží len na `127.0.0.1`.

**Za reverse proxy si token ustráž sám.** Kontrola vyššie pozerá na bind adresu, a hub
za proxy bindne na `127.0.0.1` — takže nevystrelí, hoci je hub cez proxy verejný. Preto
hub pri štarte bez jediného tokenu vypíše `POZOR: hub beží bez jediného tokenu`. Nechaj
ho otvorený len vtedy, keď sa na port naozaj nikto zvonka nedostane.

**Tokeny per agent.** Hlavný token (`TRADEBOT_HUB_TOKEN`) je správcovský a nepatrí na
servery. Každý agent dostane vlastný token, ktorý ho zároveň **identifikuje**:

```bash
PY -m tester.hub token add srv-01          # vypíše token — raz; potom je v tokens.json
PY -m tester.hub token list
PY -m tester.hub token rm srv-01
```

Príkaz ide cez API s tokenom z `tester/agent.json` (musí to byť hlavný), alebo
`--local` priamo nad `tester/hub_data/` na stroji hubu (v kontajneri `docker compose
exec hub …`); bežiaci hub si zmenu súboru všimne sám. Stav hubu presunie inam
`TRADEBOT_HUB_DATA=<adresár>` (platí pre `serve` aj pre `--local` príkazy — druhý, skúšobný
hub na tom istom stroji bez zásahu do `tester/hub_data/`). S vlastným tokenom sa agent hlási
len pod svojím menom, zadáva len ako on, výsledky sťahuje len k svojim výpočtom a rušiť
smie len to, čo zadal alebo počíta; parametre cudzieho behu neuvidí. Prepínanie
`accept` z hubu a správa tokenov sú len pre správcu. Hub bez jediného tokenu (vývoj na
localhoste) je otvorený.

**Log udalostí.** Hub zapisuje každú udalosť do `tester/hub_data/events.jsonl` (riadok
na udalosť, rotuje pri 20 MB): `agent_online`, `agent_offline`, `agent_bye`,
`job_submitted`, `job_assigned`, `job_started`, `job_finished` (stav, agent, chyba,
behy), `job_cancel` (kto), `job_requeued`, `job_timeout`, `accept_request`,
`accept_forced_off` (obchodný stroj hlásil prijímanie), `token_added`, `token_removed`.

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
PY -m tester.hub setup --name nas-win11 --role live --send   # obchodný stroj (NT8/MT5), nikdy nepočíta
PY -m tester.hub setup --max-parallel 4                     # strop behov naraz
```

Zapíše `tester/agent.json` (gitignored; premenné `TRADEBOT_HUB_URL`, `TRADEBOT_HUB_TOKEN`,
`TRADEBOT_HUB_NAME`, `TRADEBOT_HUB_ROLE`, `TRADEBOT_HUB_ACCEPT`, `TRADEBOT_HUB_SEND`, `TRADEBOT_HUB_ADMIN_TOKEN` ho
prebijú — pre Docker). `admin_token` (hlavný token hubu) patrí len do configu webapp, z ktorej
sa spravujú live účty a nasadenia (karta Live); počítajúci agent ho nemá mať.
Agent potrebuje to isté, čo každý klon: `.venv` zo setup skriptu a zložený sklad sviečok
(`PY -m tester.data_archive merge`; headless agent si ho zloží sám).

Agent beží dvoma spôsobmi:

| | príkaz | kedy |
|---|---|---|
| **webapp** | `./webapp.sh` (agent štartuje s ňou, keď `agent.json` existuje) | stroj, na ktorom niekto aj klikne |
| **headless** | `PY -m tester.hub agent` | server bez prehliadača — počítací (`compute`) alebo obchodný (`live`) |

Čo je ktorý stroj, je v „Druhy agentov“ vyššie.

## Docker

Dva samostatné compose súbory, oba sa spúšťajú z koreňa repozitára (Docker tu pri písaní
nebol k dispozícii — build nebol overený, súbory sú podľa `docker/docker-compose.yml`):

**Hub** — malý image bez Freqtradu (`docker/Dockerfile.hub`), stav vo volume `hub_data`,
kód vo volume `hub_code` (aktualizuje sa sám, viď nižšie):

```bash
cp .env.example .env         # TRADEBOT_HUB_TOKEN=… (povinný), TRADEBOT_HUB_BIND, TRADEBOT_HUB_PORT
docker compose --env-file .env -f docker/docker-compose.hub.yml up -d --build
docker compose --env-file .env -f docker/docker-compose.hub.yml exec hub python -m tester.hub token add srv-01 --local
docker compose --env-file .env -f docker/docker-compose.hub.yml exec hub python -m tester.hub events --local
```

**`--env-file .env` a koreň repozitára nie sú ozdoba.** Compose číta `.env` pre `${…}`
z adresára compose súboru (teda z `docker/`), nie z koreňa; `env_file` v službe len
podáva premenné dovnútra kontajnera. Bez toho prepínača — alebo s prázdnym tokenom —
skončíš na `required variable TRADEBOT_HUB_TOKEN is missing a value`.

Port sa predvolene viaže na `127.0.0.1` — pred hub patrí reverse proxy s TLS (Caddy,
nginx). `TRADEBOT_HUB_BIND=0.0.0.0` ho dá priamo na sieť, ale potom ide token po HTTP.

### Chudý klon: čo agent z repozitára vôbec ťahá

Repozitár nesie aj dáta: `data_archive/` (~2 GB sviečok po rokoch) a `tester/runs/`
(história behov, dnes cez 6 GB). Tester ich chce, ale **stroj, ktorý len počíta, z nich
potrebuje nanajvýš archív toho, na čom počíta** — a každý `git pull` mu ich aj tak ťahá.

```bash
python -m tester.hub sparse                     # čo je nastavené
python -m tester.hub sparse --no-history        # bez cudzej histórie behov (6 GB)
python -m tester.hub sparse --data binance      # archív len z binance (namiesto 2 GB)
python -m tester.hub sparse --no-data           # bez archívu (sklad `data/` ostáva)
python -m tester.hub sparse --off               # späť celý strom
```

Nastavia sa tým dve veci gitu naraz: **sparse-checkout** (čo má byť v pracovnom strome)
a **partial clone** (`remote.origin.partialclonefilter=blob:none` — obsah súborov mimo
výberu sa ani nesťahuje; keby ho niečo predsa chcelo, git si ho dotiahne sám). Samotný
sparse-checkout by všetko stiahol a len nezapísal na disk.

Dve veci, ktoré treba vedieť:

- **Čo už v klone je, sa z `.git` nezmaže** — chudé je až to, čo pribudne.
- Vyradené súbory **zmiznú z pracovného stromu**: s `--no-history` prestane byť
  `tester/runs/` v histórii webapp a nedá sa z neho pushovať. Na stroji, ktorý je zároveň
  testerov, to preto nerob — tam má zmysel nanajvýš `--data <zdroj>`.

Sklad sviečok (`data/`, gitignored) ostáva nedotknutý, takže agent, ktorý má dáta už
zložené, počíta ďalej aj s `--no-data`. Nové trhy mu ale nepribudnú — keď dostane výpočet
na páre, ktorý nemá, beh zlyhá s chybou o chýbajúcich dátach.

### Hub sa aktualizuje sám

Kód hubu **nie je z image**, ale z plytkého klonu vo volume `hub_code`, ktorý pri prvom
štarte vyrobí `docker/hub-entrypoint.sh` (`git init` + `fetch --depth 1` + `reset`;
repozitár je verejný, takže bez tokenu). Hub nepočíta, takže ten klon je rovno chudý
(`--filter=blob:none` + sparse-checkout, pravidlá sú `sparse.HUB_RULES`): bez sviečok,
bez histórie behov, bez C# jadra — pár megabajtov namiesto deviatich gigabajtov. Bežiaci hub si ho potom drží aktuálny sám
(`tester/hub/update.py`):

1. každých `TRADEBOT_HUB_UPDATE` minút (default 5) `git fetch` + `reset --hard` na
   `origin/${TRADEBOT_HUB_BRANCH:-main}`,
2. keď sa `HEAD` zmenil, **prestane prideľovať** výpočty z fronty a **počká, kým dobehnú
   bežiace** — žiadny výpočet v stave `assigned`, `running` ani `cancelling` (každých 10 s
   sa pozrie znova); nové zadania idú len do fronty (bez `--queue` ich hub odmietne),
   fronta reštart pokojne prežije v `state.json` a rozdelí ju hub na novom kóde,
3. potom proces skončí a `restart: unless-stopped` ho zdvihne na novom kóde.

Výpadok je pár sekúnd: agenti heartbeat zopakujú a keď ich hub medzitým zabudne, sami sa
prihlásia znova. Karta Hub ukazuje pri agentoch, na akom kóde hub beží a či čaká na reštart
(`hub A → B`). Keby niektorý výpočet bežal neúmerne dlho, poistka je
`TRADEBOT_HUB_UPDATE_MAX_WAIT` (minúty; 0 = čakaj, koľko treba). Vypnúť sa to dá
`TRADEBOT_HUB_UPDATE=0`, mimo Dockeru sa to zapína `--update MIN`. Na klone so zmenenými sledovanými
súbormi (vývojársky klon) sa aktualizácia odmietne a v logu povie, ktoré súbory by `reset --hard` zmazal.

**Rebuild image treba len pri zmene `Dockerfile.hub`** (alebo závislostí) — zmena kódu
hubu sa dostane do prevádzky sama. Klon vo volume je jednorazový: nikto doň nepíše, preto
`reset --hard`. Keby sa mal zahodiť, stačí `docker volume rm tradebot-hub_hub_code` (stav
v `hub_data` je vedľa a ostane).

**Headless agent** — image `docker/Dockerfile.agent` stavia na image Freqtradu s jadrom
(`docker compose -f docker/docker-compose.yml build freqtrade` najprv) a pridáva git:

```bash
# .env: TRADEBOT_HUB_URL, TRADEBOT_HUB_TOKEN (token TOHTO agenta), TRADEBOT_HUB_NAME, TRADEBOT_HUB_MAX_PARALLEL
docker compose --env-file .env -f docker/docker-compose.agent.yml up -d --build
docker compose --env-file .env -f docker/docker-compose.agent.yml logs -f
```

Kontajner mountuje z hostiteľa `tester/` (história, stav agenta), `data/` a
`data_archive/` (sklad sviečok; chýbajúce si zloží pri štarte), `deploy/freqtrade/`,
`tradebot/` (read-only) a `.git/` (read-only, len na verziu). **`git pull` sa v kontajneri
nerobí** (`TRADEBOT_HUB_PULL=off`) — rob ho na hostiteľovi; agent zmenu kódu na disku
spozná, dočíta, čo počíta, odhlási sa a skončí, a `restart: unless-stopped` ho zdvihne na
novom kóde. Výpočet s commitom, ktorý hostiteľ ešte nepullol, zlyhá s chybou, ktorá to
povie. Push/Pull histórie behov sa robí z hostiteľa.

**Pull na hostiteľovi — časovač aj hneď na ⟳.** Pull robí `docker/host-pull.sh <klon>` (ako
používateľ, ktorému klon patrí). Spúšťa ho systemd jednotka z časovača (napr. každých 10 min) a
s `TRADEBOT_HUB_PULL=host` (v `.env` alebo override) aj path jednotka: tlačidlo ⟳ na karte Hub
zapíše pokyn do `tester/hub_pull_request`, path jednotka spustí pull hneď a skript dá výsledok
do `tester/hub_pull_result` (pokyn, návratový kód, výstup). Agent ho nahlási hubu (pri chybe čip
„pull zlyhal" s výstupom gitu); keď hostiteľ do 3 min neodpovie, nahlási, že path jednotka chýba.
Bez nej nastav `off` — ⟳ potom len povie, že kód stiahne časovač.

```ini
# /etc/systemd/system/tradebot-agent-pull.service
[Service]
Type=oneshot
User=morky
ExecStart=/bin/sh /cesta/klon/docker/host-pull.sh /cesta/klon

# /etc/systemd/system/tradebot-agent-pull.path   (systemctl enable --now …path)
[Path]
PathChanged=/cesta/klon/tester/hub_pull_request
Unit=tradebot-agent-pull.service
[Install]
WantedBy=paths.target
```

**Vlastné úpravy na tomto stroji.** Compose súbory v `docker/` sú spoločné a verzované;
nemeň ich, keď ide len o tento server. Nastavenia sa dajú zmeniť bez dotyku gitu:

- `.env` v koreni (gitignored) — tokeny, adresa hubu, bind, port, `TRADEBOT_HUB_NAME`,
  `TRADEBOT_HUB_MAX_PARALLEL`;
- **override súbor** `docker/*.local.yml` alebo `docker/*.override.yml` (oba gitignored) na čokoľvek ostatné — iné mounty,
  limity CPU a pamäte, sieť, vlastný `command`. Compose ho zlúči nad základný:

```bash
docker compose -f docker/docker-compose.agent.yml -f docker/agent.local.yml up -d --build
```

```yaml
# docker/agent.local.yml — do gitu nejde
services:
  agent:
    deploy:
      resources:
        limits: {cpus: "6"}
    volumes:
      - /mnt/ssd/data:/app/data
```

Gitignored je aj `docker/Dockerfile.*.local`, keby si potreboval vlastný image.

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

**Plán (voliteľné).** Hub vidí len to, čo už dostal — hľadanie, ktoré posiela výpočty
postupne, by nevedelo povedať, kedy skončí. Kto ide dať **veľa** výpočtov, pripíše pri zadaní
`--plan-total N` (koľko ich dá spolu, aj tie, čo ešte nie sú zadané) a voliteľne `--plan-done M`
(koľko už má hotových, aj mimo hubu); vo formulári pri „na hube" polia **plán: spolu /
hotových**. Kto dáva pár behov, nepíše nič. Žiadne meno ani extra rozhranie: plán patrí
zadávateľovi a hub doň započíta každý jeho ďalší výpočet (hotových = väčšie z nahláseného
a napočítaného; `--plan-done` stačí poslať, keď sa zmení). Karta Hub nad výpočtami ukáže
tabuľku plánov: hotových / spolu / zostáva / počíta a **kedy to dobehne** pri rýchlosti plánu
za poslednú hodinu (inak celého hubu). Hotový plán zmizne po 2 dňoch, neobnovovaný po 14;
nové `--plan-total` po hotovom začne nový (`tester/hub/plans.py`). **AI, ktorá zadáva veľkú
dávku na hub, plán pripíše**, keď aspoň zhruba vie, koľko výpočtov bude — aby sa dalo
plánovať, čo pôjde po nej.

```bash
PY -m tester.webapp.cli run --remote --queue --plan-total 20000 --plan-done 300 --profile … --note "…"
```

## Webapp

Karta **Hub** má hore **Nastavenie**: meno agenta, adresa hubu, token, koľko behov naraz,
prijímať a posielať. **Uložiť a pripojiť** zapíše `tester/agent.json` a agenta hneď
spustí — bez reštartu webapp (to isté ako `python -m tester.hub setup`). **Odpojiť**
agenta odhlási a nastavenie zmaže. Pod tým je stav tohto agenta (online,
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
  povie v heartbeate a agent si to zapíše do configu. Obchodnému stroju (rola `live` alebo
  live nasadenie) sa prijímanie zapnúť nedá.
- **Strop na čas behu.** Zaseknutý Freqtrade by držal výpočet v `running` donekonečna.
  Agent preto beh zabije po `--max-runtime MIN` (v CLI alebo cez API), inak po
  trojnásobku odhadu, najmenej 10 minút; výpočet skončí ako `failed` s chybou, ktorá
  strop uvedie. Hub je poistka: to isté vymáha o dva heartbeat intervaly neskôr.
- **Viac seedov.** `cli hyperopt --remote --seeds 3` pustí ten istý hyperopt s tromi
  seedmi (od `--seed` alebo 1) naraz na hube a na konci porovná víťazov: `ROVNAKE`, keď
  všetky skončili na tých istých hodnotách (optimum nie je náhoda jedného behu), `ROZNE`,
  keď nie (priestor je plochý alebo šum — presná hodnota nerozhoduje, over cez plateau).
  Je to náhrada za delenie hyperoptu medzi stroje, ktoré Freqtrade nedovolí.

## Pluginy

Vlastný kód, ktorý beží **v procese hubu** (`hub serve`) a hub ho nepozná menom — ako stratégie
v registry. Plugin = balík `tester/hub/plugins/<meno>/`, ktorý vystaví `PLUGIN = <podtrieda HubPlugin>`
(`tester/hub/plugins/base.py`). Do Docker image ide sám (`COPY tester/hub/`) a s ním aj samoaktualizácia.

| plugin | čo robí |
|---|---|
| `watchdog` | stroje s aktívnym nasadením, ktoré sa neozvali / znova hlásia, a ostatné pluginy, keď sa nenačítali, padajú dlhšie ako 5 min, visia alebo samy hlásia `problem` (docs/LIVE.md, „Strážca (hub)“) |
| `ff_calendar` | červené (High impact) správy z kalendára ForexFactory → upozornenie do Telegramu pred udalosťou |
| `livedata` | živé dáta stratégií (sviečky vrátane 1m, obchody) zo `live.sqlite` do mesačných feather; uzavreté mesiace raz za mesiac push do gitu (`data_live/`), zvyšok ponúka webapp (docs/DATA.md §D) |

**Kontrakt.** `PluginHost` dá každému pluginu vlastné vlákno a volá `tick()` každých `interval`
sekúnd; výnimka hub nezhodí, zapíše sa do stavu (`errors`, `error_since`, `last_error`) a ohlási ju
`watchdog`. Plugin vidí len `PluginContext`:

| | |
|---|---|
| `ctx.dir` | `hub_data/plugins/<meno>/` (`HUB_PLUGINS_DIR`) — config, stav, zásoba; gitignored |
| `ctx.config()` | `config.json` z toho adresára, znova pri zmene súboru; `"enabled": false` plugin vypne bez reštartu |
| `ctx.notify(text)` | Telegram hubu (`hub_data/telegram.json`, HTML, `[label]` pred textom); zlyhanie = `NotifyError`, plugin si zmenu nechá na ďalší tick. Token plugin nevidí |
| `ctx.log`, `ctx.event(…)` | log a log udalostí hubu (`plugin_<event>`) |
| `ctx.hub` | stav hubu (agenti, nasadenia) — len na čítanie |
| `ctx.plugins()` | stav všetkých pluginov (pre strážcu) |

Voliteľne `files()` + `files_root()` (súbory na stiahnutie cez `GET /api/plugins/<meno>/files[/<cesta>]` —
hub vydá len to, čo je v zozname a leží pod `files_root`), `status()` (čo ukázať; kľúč `problem` = text pre strážcu), `cli(argv)` (príkaz na stroji
hubu), `views()` + `view(meno)` (pohľady pre Telegram agenta: meno → text gombíka a HTML pohľadu —
agent ich ukáže v klávesnici, docs/LIVE.md, „Príkazy (agent)“), `teardown()`, `max_tick` (dlhší tick = visí),
`default_enabled`.

```bash
python -m tester.hub plugins            # stav bežiaceho hubu cez API (GET /api/plugins)
python -m tester.hub plugins --local    # čo je na disku stroja hubu
python -m tester.hub plugin ff_calendar --fetch     # príkaz pluginu; v kontajneri cez docker compose exec hub …
```

### Živé dáta (`livedata`)

Každých 5 minút prepíše sklad telemetrie hubu (`live.sqlite`) do `hub_data/plugins/livedata/data_live/`
(`tester.livedata`: mesačné feather sviečok — aj 1m `m1` — a obchodov, popisy inštancií; docs/DATA.md §D).

- **Push do gitu**: od `push_day`. dňa mesiaca (UTC, predvolene 2.) idú súbory **uzavretých** mesiacov a popisy
  inštancií do `data_live/` na `branch`. Z vlastného klonu `hub_data/plugins/livedata/repo` (plytký, partial,
  sparse len `data_live/`), nie z klonu, z ktorého hub beží — ten si `update` tvrdo prepisuje. Predbehnutý push
  (iný commit) sa zopakuje. Commit vznikne len pri zmene obsahu; zlyhaný push sa skúša každú hodinu a po dni ho
  ohlási strážca.
- **Webapp** si cez `GET /api/plugins/livedata/files` stiahne súbory, ktorých obsah v gite ešte nie je.

`hub_data/plugins/livedata/config.json`:

```json
{"remote": "git@github.com:materko/imbalance_strategy.git", "ssh_key": "deploy_key",
 "branch": "main", "push_day": 2, "author": "TradeBot hub <hub@tradebot.local>"}
```

`ssh_key` je **deploy kľúč** repozitára s právom zápisu (len tento repozitár): súkromná časť leží v adresári
pluginu (`deploy_key`, 600), verejná je v GitHube pri repozitári (Settings → Deploy keys), `known_hosts` si
plugin uloží pri prvom spojení. Vyrobí sa takto (na stroji hubu; verejnú časť pridať s právom zápisu):

```bash
ssh-keygen -t ed25519 -N "" -C "tradebot-hub livedata" -f hub_data/plugins/livedata/deploy_key
gh repo deploy-key add hub_data/plugins/livedata/deploy_key.pub --allow-write --title "tradebot-hub livedata"
```

Bez `ssh_key` je `remote` HTTPS s tokenom (`https://x-access-token:<token>@github.com/…`, fine-grained token
s *Contents: write*); môže prísť aj z env `TRADEBOT_LIVEDATA_REMOTE`. Bez `remote` plugin dáta drží a ponúka
webapp, ale nepushuje. Token sa do logu ani chýb nedostane (`***`). Image hubu potrebuje pandas, pyarrow
a openssh-client (`Dockerfile.hub`) — **po tejto zmene raz `up -d --build`**.

```bash
python -m tester.hub plugin livedata            # čo je mimo gitu, čo čaká na push, posledný commit
python -m tester.hub plugin livedata --export   # export hneď
python -m tester.hub plugin livedata --push     # push uzavretých mesiacov hneď (aj pred push_day)
```

### Kalendár ForexFactory (`ff_calendar`)

Zdroj je oficiálny export kalendára (`forexfactory.com/calendar` → Export):
`https://nfs.faireconomy.media/ff_calendar_thisweek.json` — aktuálny týždeň (nedeľa–sobota
podľa New Yorku). **Čas je v ňom New York s posunom** (`2026-10-14T08:30:00-04:00`), takže prevod
na `tz` (predvolene `Europe/Bratislava`) je presný aj v týždňoch, keď USA a Európa menia letný čas
v iné dni: CPI o 8:30 v New Yorku = 14:30 v Bratislave.

`hub_data/plugins/ff_calendar/config.json` (všetko voliteľné, toto sú predvolené):

```json
{"impact": ["High"], "currencies": [], "lead_min": 30, "count": 1, "every_min": 10,
 "tz": "Europe/Bratislava", "refresh": "07:00"}
```

- `lead_min` / `count` / `every_min` — prvé upozornenie toľko minút pred, koľkokrát spolu, odstup
  (60/3/20 → 60, 40 a 20 min pred). Namiesto nich `"remind_min": [60, 15, 5]`; 0 = v čase udalosti.
- `currencies` — prázdne = všetky meny, inak napr. `["USD", "EUR"]`; `impact` aj `["High", "Medium"]`.
- `chats` — iné chaty ako v `telegram.json` hubu.
- `refresh` — **sťahuje sa raz denne** v tento čas. Navyše, keď export ešte drží minulý týždeň
  (prehadzuje sa v nedeľu), skúša to každú hodinu — inak by vypadli pondelkové ranné ázijské správy.
  Neúspech = ide sa zo zásoby (`cache.json`) a skúsi sa o 15 min.

Správa: `🔴 o 30 min · 14:30` a riadok na udalosť (`USD CPI m/m · progn. 0.6% · pred. 0.4%`);
udalosti v tom istom čase idú v jednej správe. Čo odišlo, je v `state.json` (udalosť → minúty pred),
takže reštart hubu nič nezopakuje; keď hub v čase upozornenia nebežal, príde jedno oneskorené
(„o 7 min“), kým udalosť nenastala. Bez úspešného stiahnutia 26 h, alebo keď export 12 h po začiatku
týždňa stále nemá nový, hlási plugin `problem` a `watchdog` ho pošle do Telegramu.

V Telegrame je gombík **📅 Udalosti** (pohľad `upcoming`): sledované udalosti zvyšku týždňa po dňoch
v čase `tz`, s prognózou a ✓ pri tých, ku ktorým už upozornenie odišlo.

`python -m tester.hub plugin ff_calendar` vypíše sledované udalosti týždňa v čase hubu a kedy k nim
príde upozornenie; `--fetch` stiahne export hneď, `--test` pošle najbližšiu udalosť do Telegramu.

Testy: `tester/tests/test_hub_plugins.py`.

## API hubu

Všetko pod `/api/`, s tokenom; `/api/health` bez neho.

| volanie | kto | čo |
|---|---|---|
| `POST /api/agents/register` | agent | meno, jadrá, sloty, `accept`, `send` |
| `POST /api/agents/{name}/heartbeat` | agent | stav výpočtov + lokálna záťaž → `assign`, `cancel`, `finished`, `set_accept` |
| `POST /api/agents/{name}/accept?value=` | správca | zapnúť/vypnúť prijímanie na agentovi |
| `POST /api/hub/drain?stop=&by=`, `DELETE /api/hub/drain` | správca | drain pred ručným reštartom hubu (vyššie); stav v `GET /api/status` → `drain` |
| `DELETE /api/agents/{name}?force=&token=` | správca | vyhodiť agenta zo zoznamu (premenovaný stroj) |
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
| `GET /api/plugins` | ktokoľvek | pluginy hubu a ich stav (vyššie) |
| `GET /api/plugins/views`, `GET /api/plugins/{name}/views/{view}` | ktokoľvek | pohľady pluginov pre Telegram agenta (`[{plugin, view, label}]`, `{text}`) |
| `POST /api/live/events` | agent | dávky udalostí zo spoolu bežiacich stratégií (`{"agent", "batches": [{instance, session, events}]}` → `{"accepted"}`) |
| `GET /api/live/instances[/{id}]`, `…/{id}/events`, `…/{id}/snapshot`, `GET /api/live/export` | ktokoľvek | live telemetria (nižšie) |
| `GET /api/live/accounts[/{id}]`, `GET /api/live/deployments[/{id}]`, `GET /api/live/audit?limit=` | ktokoľvek | požadovaný stav live nasadení (nižšie) |
| `POST /api/live/accounts`, `PATCH/DELETE /api/live/accounts/{id}?force=`, `POST /api/live/deployments`, `PATCH/DELETE /api/live/deployments/{id}?force=` | správca | zmeny účtov a nasadení (`?by=` = meno človeka do auditu) |
| `POST /api/live/agents/{name}/update {version?, force?}`, `DELETE …/update` | správca | nový kód na stroji agenta (fáza 2c, nižšie) |

### Live telemetria

Agent na obchodnom PC (NinjaTrader 8, MetaTrader 5) v kole `work()` číta spool platforiem
(`tradebot.live.SpoolReader`, kurzor `tester/live/cursor.json`) a posiela ho na hub
(`LiveShipper` → `POST /api/live/events`); kurzor posunie až po 200. Hub ukladá do
`tester/hub_data/live.sqlite` idempotentne (`tradebot.live.store.LiveStore`), webapp si
udalosti zrkadlí cez `GET /api/live/export?after=`. Celá cesta dát, identita inštancie
a schéma udalostí: [LIVE.md](LIVE.md). Ručne: `python -m tradebot.live status|tail|ship`.

### Live nasadenia (fáza 2b)

Opačným smerom nesie hub **požadovaný stav** — čo má na ktorom stroji bežať
(`tradebot.live.deploy.DeployStore`, tabuľky `accounts`, `deployments`, `audit`, `applied`
v tom istom `live.sqlite`). Účet = agent (stroj) + platforma + login/server/terminál;
nasadenie = účet + stratégia + symbol + TF + profil so snímkou configu (`config`,
`config_hash` = sha256 kanonického JSON) + režim (`enabled`/`paused`/`flatten`) + `active`.
Z toho hub odvodí `instance` (`schema.instance_id`, identita účtu MT5 `<login>-<server>`,
inak `login`) a v odpovedi nasadenia pridá `applied` (čo agent naposledy potvrdil) a `live`
(inštancia zo spoolu: `seen`, `alive` = udalosť do 3 barov TF, `last_bar_ms`, `session`).

- **Mutácie len s hlavným tokenom** (`TRADEBOT_HUB_TOKEN`); token agenta číta. Webapp na to
  má `admin_token` v `tester/agent.json` (alebo `TRADEBOT_HUB_ADMIN_TOKEN`) — bez neho je jej
  karta Live len na čítanie. Hlavný token na počítajúce agenty nepatrí.
- **Účet nie je viazaný na stroj** — stroj (`agent`) a pri MT5 terminál sú v nasadení.
  **Heslo** účtu (`password` v POST/PATCH, len MT5) hub drží šifrované (`secret.key` vo
  volume `hub_data` vedľa `live.sqlite`, alebo `TRADEBOT_HUB_SECRET_KEY`) a pošle ho v heartbeate
  každému stroju s nasadením na účte, kým ten aktuálnu verziu nepotvrdí (`secret_ack`). V žiadnom
  zozname nie je, len `secret` (uložené?) a `secret_waiting` (ktoré stroje ho ešte nemajú). Bez
  `secret.key` sa heslá nedajú rozšifrovať — zálohuj ho spolu s `live.sqlite`.
- **Heartbeat** nesie navyše: agent → `live: {instances, applied: [{deployment, config_hash,
  mode, status ok|pending|error|removed, error}], drivers, secret_ack}`, hub → `live:
  {accounts, deployments}` = celý požadovaný stav toho agenta (účty jeho nasadení so `secret`,
  keď čaká, a s `rev`; nasadenia s `config`). Starý agent `live` neposiela a nič sa nedeje; `applied` cudzieho nasadenia
  hub ignoruje. Čo agent hlási, je v `GET /api/agents` (`live.drivers`, počet inštancií)
  a v `/api/status` (`live_instances`).
- **Mazanie**: `DELETE` nasadenia ho najprv vypne (`active=false`, agent ho z platformy
  odstráni); naozaj zmazať sa dá, keď agent potvrdil (`applied` po deaktivácii) alebo ho
  nikdy nevidel, inak `?force=true`. Účet s nasadeniami len s `force` (zmažú sa aj tie).
- Každá zmena je v `audit` (`GET /api/live/audit`, kto, akcia, staré/nové) a v logu
  udalostí hubu (`live_account`, `live_deployment`).

### Nový kód na stroji (fáza 2c)

Nasadenie nesie `version` (commit zadávateľa, inak commit hubu — `HubState.version`), agent hlási
v heartbeate `live.installed` (commit, z ktorého je kód na každej platforme — marker `installed.json`)
a hub z toho robí `code_state` (`ok`/`outdated`/`unknown`; `ok` aj keď je stroj novší — `git
merge-base --is-ancestor` v klone hubu) pri nasadení aj pri agentovi (`GET /api/agents` →
`live.code_state`, `live.code_update`, `code_target`).

`POST /api/live/agents/{name}/update {version?, force?}` (správca, `?by=`) uloží agentovi
`code_target`; hub ho posiela v heartbeate (`live.code_target`), kým agent nehlási `live.code_update`
so `status: ok` pre tú verziu (udalosti `code_update_request`, `code_update_done`, riadok v audite).
Agent pullne chýbajúci commit, overí bránu (nasadenia v pauze/flatten a bez pozície; `force` ju
preskočí), zavolá `install_code` driverov a po zmene HEAD sa reštartuje (headless) alebo hlási
`needs_restart` (webapp). Celý tok: [LIVE.md](LIVE.md), „Fáza 2c“.

Webapp k tomu pridáva `GET /api/hub` (stav jej agenta a hubu), `POST /api/hub/jobs`
(hotový payload z CLI), `POST /api/hub/runs` a `POST /api/hub/hyperopts` (zadanie
z formulára), `POST /api/hub/accept` (prepínač prijímania) a
`GET/POST /api/hub/jobs[/{id}[/cancel]]` a `DELETE /api/hub/agents/{name}` (vyhodenie agenta).

## Čo hub nerobí

- Nedelí jeden hyperopt medzi viac strojov. Freqtrade drží Optuna štúdiu v pamäti procesu;
  zdieľané úložisko by bol zásah do jeho privátneho API. Namiesto toho sa dá pustiť
  ten istý hyperopt s rôznym `--seed` na rôznych agentoch — keď skončia na tom istom plató,
  je to silnejší signál než jedno hľadanie s viac epochami.
- Nesynchronizuje dáta. Každý agent musí mať zložený sklad sviečok (`data_archive
  merge`); kód si pullne sám (viď „Verzia kódu"), ale len to, čo je v `main`.
- Nerobí TLS ani používateľov — token per agent je identita, šifrovanie dá reverse proxy.
