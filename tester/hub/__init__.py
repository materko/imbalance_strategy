"""Distribuované počítanie: jeden verejný **hub**, na ktorý sa hlásia **agenti**.

```
                    ┌──────────────── hub (verejný) ────────────────┐
                    │  agenti + heartbeat   fronta výpočtov   zipy  │
                    └───────▲──────────────────▲──────────────▲─────┘
      register/heartbeat    │                  │              │  výsledok (zip)
      (každých ~10 s)       │        POST /api/jobs           │
                 ┌──────────┴───┐        ┌─────┴──────┐  ┌────┴─────────┐
                 │ agent A      │        │ agent B    │  │ agent C      │
                 │ webapp,      │        │ CLI --remote│  │ headless,    │
                 │ accept=true  │        │ send=true  │  │ accept=true  │
                 └──────────────┘        └────────────┘  └──────────────┘
```

Kto je kto:

- **hub** (`tester.hub.server`, `python -m tester.hub serve`) — jediný proces s verejnou
  adresou. Drží zoznam agentov, frontu výpočtov a odovzdané výsledky. Sám nič nepočíta.
- **agent** (`tester.hub.agent`) — každý klon repozitára, ktorý má v `tester/agent.json`
  adresu hubu. Môže to byť bežiaca **webapp** (agent sa spustí s ňou) alebo **headless**
  proces (`python -m tester.hub agent`). Pravidelne sa hlási (heartbeat) a v odpovedi
  dostáva výpočty, ktoré mu hub pridelil. Konfigurácia hovorí, či výpočty **prijíma**
  (`accept`) a či ich smie **posielať** (`send`).
- **zadávateľ** (`tester.hub.client`, `cli run --remote`, `cli hyperopt --remote`) —
  agent so `send=true`. Najprv sa spýta, či je niekto voľný (`/api/capacity`), a až potom
  pošle výpočet. Keď nikto voľný nie je, hub ho zaradí do fronty **len ak zadávateľ
  súhlasil** (`--queue`), prípadne len keď odhadované čakanie nepresiahne `--max-wait`.

Prečo agent ťahá a hub netlačí: agenti sú za NAT-om a firewallom, verejnú adresu má len
hub. Heartbeat je preto zároveň kanál, ktorým výpočet k agentovi príde — oneskorenie je
najviac jeden interval (~10 s), čo je pri behoch na minúty jedno.

Kapacita: agent hlási počet jadier a koľko behov naraz zvládne (`slots`). Backtest berie
jedno jadro, hyperopt **všetky** (Freqtrade ich vyťaží cez joblib), takže vedľa hyperoptu
sa nič neplánuje a hyperopt nezačne, kým na agentovi niečo beží. Kým beží niečo menšie,
voľné jadrá sa dajú obsadiť ďalším backtestom.

Čas: agent pri každom heartbeate pošle, ako ďaleko výpočet je a koľko mu asi ostáva —
odhad z vlastnej histórie behov (`tester.hub.protocol.estimate_seconds`) a z logu
(u hyperoptu počet hotových epoch). Hub z toho vie povedať, kedy sa ktorý agent uvoľní,
a to rozhoduje, či sa výpočet do fronty dá alebo zadávateľ dostane „nikto nie je voľný".

Výsledok: agent spočíta beh do **vlastnej** histórie (`tester/runs/`), po dobehnutí
adresár behu (u hyperoptu aj overovacie behy) zabalí a odovzdá hubu; zadávateľ si ho
stiahne a rozbalí do svojej histórie — beh potom vyzerá, ako keby bežal u neho.

Bezpečnosť: hub je verejný, preto každé volanie nesie token (`TRADEBOT_HUB_TOKEN`,
hlavička `Authorization: Bearer …`). TLS nech rieši reverse proxy pred hubom.
"""
