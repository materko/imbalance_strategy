"""Prepínače príkazového riadka: podpríkazy a ich voľby."""

from __future__ import annotations

import argparse

from .analysis import cmd_analytics, cmd_decay, cmd_nulltest, cmd_paper, cmd_prop
from .common import DEFAULT_URL
from .history import (
    cmd_chart, cmd_list, cmd_params, cmd_prune, cmd_pull, cmd_push, cmd_recompute, cmd_replay,
    cmd_show, cmd_status,
)
from .hyperopt import cmd_hyperopt, cmd_hyperopts
from .matrix import cmd_checkup, cmd_matrices, cmd_matrix
from .run import cmd_run
from .sweep import cmd_plateau, cmd_portfolio, cmd_sweep, cmd_sweeps


#: kritériá výberu pre `sweep` (definícia je v `tester/sweep.py`)
_GOALS = ("break_even", "profit", "winrate", "drawdown")


def _remote_args(p: argparse.ArgumentParser) -> None:
    """Distribuované počítanie (tester.hub): beh ide na hub, spočíta ho voľný agent a
    výsledok sa vráti do tejto histórie, ako keby bežal tu. Mriežky (sweep, checkup,
    matrix, plateau) sa s `--remote` zadajú naraz a počítajú paralelne."""
    p.add_argument("--remote", action="store_true",
                   help="poslať výpočet na hub (tester/agent.json) namiesto lokálneho behu")
    p.add_argument("--queue", action="store_true",
                   help="s --remote: keď nikto nie je voľný, nechať čakať vo fronte hubu "
                        "(mriežky čakajú vždy)")
    p.add_argument("--max-wait", dest="max_wait", type=float,
                   help="s --queue: najviac toľko minút čakania podľa odhadu hubu, inak odmietnuť")
    p.add_argument("--cores", help="s --remote: koľko jadier výpočet žiada (číslo alebo all; "
                                   "default backtest 1, hyperopt a AI all)")
    p.add_argument("--max-runtime", dest="max_runtime", type=float,
                   help="s --remote: strop na čas behu v minútach; po ňom agent beh zabije "
                        "(default trojnásobok odhadu, najmenej 10 min)")


def _run_args(p: argparse.ArgumentParser, *, timerange: bool = True) -> None:
    """Argumenty spoločné pre `run` aj `sweep` — nech sa nemôžu rozísť.

    `checkup` beží na piatich oknách naraz, takže jediné `--timerange` nemá; všetko
    ostatné (profil, pár, poplatok, peňaženka) má rovnaké, a preto to je tu.
    """
    p.add_argument("--strategy", default="ibs", help="stratégia z registry (default ibs)")
    p.add_argument("--profile", help="východiskový profil z tradebot/strategies/<stratégia>/configs/ alebo cesta k JSON (bez neho Pine defaulty)")
    p.add_argument("--set", action="append", metavar="KLUC=HODNOTA", help="zmena parametra, opakovateľné")
    p.add_argument("--pair", help="napr. BTC/USDT:USDT alebo ETH/USDT:USDT (default podľa profilu)")
    if timerange:
        p.add_argument("--timerange", required=True, help="YYYYMMDD-YYYYMMDD")
    p.add_argument("--timeframe", default=None,
                   help="TF grafu, na ktorom stratégia počíta (bez neho default stratégie, "
                        "napr. ibs 3m, structure 5m; ako TF grafu v TradingView)")
    p.add_argument("--exchange", choices=("tester", "binance", "coinbase", "dukascopy"),
                   help="burza pre Freqtrade beh (predvolene fiktivna 'tester', ktora pozna "
                        "vsetky nase timeframy)")
    p.add_argument("--engine", choices=("freqtrade", "multicharts"),
                   help="čím beh prehrať: freqtrade alebo multicharts (emulátor); "
                        "bez neho podľa toho, aké dáta pár má")
    p.add_argument("--fee", type=float, default=None,
                   help="poplatok na stranu ako podiel; bez neho podľa trhu "
                        "(krypto 0.0005, CFD polovica spreadu)")
    p.add_argument("--wallet", type=float, default=10000)
    p.add_argument("--no-detail", action="store_true", help="bez 1m detailu fillov (rýchlejšie, hrubšie)")
    p.add_argument("--note", help="poznámka do histórie — napíš, čo beh testuje")
    p.add_argument("--user", help="meno testera (default TRADEBOT_USER)")
    _remote_args(p)
    # AI vrstva (FreqAI) - filter nad portom. Bez `--ai` sa nic nemeni a parita s Pine
    # ostava; so zapnutou sa obchodov ubuda, takze je to rozsirenie mimo Pine.
    p.add_argument("--ai", action="store_true",
                   help="zapni AI filter (FreqAI): model rozhodne, ktorý signál brať")
    p.add_argument("--ai-min-prob", type=float, dest="ai_min_prob",
                   help="prah istoty, pod ktorým sa signál preskočí (default 0.55)")
    p.add_argument("--ai-train-days", type=int, dest="ai_train_days",
                   help="dĺžka tréningového okna v dňoch (default 180)")
    p.add_argument("--ai-backtest-days", type=int, dest="ai_backtest_days",
                   help="ako často sa pretrénuje, v dňoch (default 30)")
    p.add_argument("--ai-model", dest="ai_model",
                   help="model FreqAI (default LightGBMClassifier)")
    p.add_argument("--ai-adjust", dest="ai_adjust", action="append",
                   metavar="KLUC=OD:DO",
                   help="čo smie model meniť podľa istoty, napr. `size=0.5:1.5` alebo "
                        "`tp=0.8:1.4`; opakovateľné. Zoznam kľúčov danej stratégie "
                        "vypíše `ai-adjust` bez hodnoty")


def build_parser(description: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m tester.webapp.cli", description=description,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL, help="adresa webapp (default %(default)s, alebo TRADEBOT_WEB_URL)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("run", help="spusti backtest (cez webapp, alebo priamo) a ulož do histórie")
    _run_args(p)
    p.add_argument("--no-wait", action="store_true", help="len zaradiť do fronty webapp, nečakať")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("sweep", help="mriežka behov cez hodnoty parametra a výber podľa kritéria")
    p.add_argument("--param", action="append", required=True, metavar="NAZOV=HODNOTY",
                   help="rozsah `od:do:krok` alebo zoznam `a,b,c`; dá sa opakovať")
    p.add_argument("--goal", choices=tuple(_GOALS), default="break_even",
                   help="podľa čoho vybrať najlepší beh (default break-even poplatok)")
    p.add_argument("--max-dd", type=float, help="strop na max drawdown v %%")
    p.add_argument("--min-trades", type=int,
                   help="minimálny počet obchodov za rok (prepočíta sa na dĺžku okna), inak je bod mimo")
    p.add_argument("--max-runs", type=int, default=0,
                   help="strop na veľkosť mriežky; 0 (default) = bez stropu, sweep smie bežať "
                        "cez noc. Cena je čas: rok backtestu je asi 30 s na bod")
    _run_args(p)
    p.set_defaults(func=cmd_sweep)

    p = sub.add_parser("portfolio", help="vybrané behy ako portfólio: koľko a za aký drawdown")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--account", type=float, default=10000.0, help="účet (default 10000)")
    p.add_argument("--risk", type=float, default=1.0,
                   help="riziko na obchod v %% pre rozpis po rokoch (default 1)")
    p.add_argument("--risks", help="riziká do tabuľky oddelené čiarkou (default 0.25,0.5,1,2,3)")
    p.add_argument("--min-trades", type=int, default=10, help="beh s menej obchodmi sa vynechá")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(func=cmd_portfolio)

    p = sub.add_parser("plateau", help="okolie víťaza hyperoptu — je to plató alebo špička?")
    p.add_argument("hyperopt_id", help="beh hyperoptu z histórie")
    p.add_argument("--iterations", type=int, default=2000, help="opakovaní Monte Carla (default 2000)")
    p.add_argument("--seed", type=int, default=12345)
    # Nastavenie behu (par, okno, poplatok, profil) sa berie z vitaza, nie z prikazu -
    # sused sa musi lisit LEN v tom jednom parametri, inak sa neporovnava okolie.
    p.add_argument("--note", default="", help="poznámka k susedným behom")
    p.add_argument("--user", help="meno testera (inak TRADEBOT_USER)")
    p.add_argument("--no-wait", action="store_true", help="nečakať na dobehnutie")
    _remote_args(p)
    p.set_defaults(func=cmd_plateau)

    p = sub.add_parser("nulltest", help="je edge odlíšiteľný od náhody? (porovnanie s náhodným vstupom)")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--null", choices=("anytime", "session"),
                   help="typ náhody; bez neho sa spočítajú obe a porovnajú")
    p.add_argument("--iterations", type=int, default=1000, help="koľko náhodných behov (default 1000)")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--limit", type=int, default=40, help="najviac toľko behov (default 40)")
    p.set_defaults(func=cmd_nulltest)

    p = sub.add_parser("paper", help="meranie do docs/merania/ zo všetkého, čo vieme")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--strategy", default="ibs", help="stratégia (default ibs)")
    p.add_argument("--title", default="", help="nadpis dokumentu")
    p.add_argument("--name", default="", help="názov súboru (inak MERANIE_<strategia>_<trh>_<datum>.md)")
    p.add_argument("--risk-pct", type=float, default=1.0, dest="risk_pct",
                   help="riziko na obchod pre portfólio v %% (default 1)")
    p.add_argument("--iterations", type=int, default=400,
                   help="opakovaní testu proti náhode (default 400)")
    p.add_argument("--limit", type=int, default=40, help="najviac toľko behov (default 40)")
    p.add_argument("--stdout", action="store_true", help="vypísať, nezapisovať súbor")
    p.set_defaults(func=cmd_paper)

    p = sub.add_parser("analytics", help="uložené analytiky (per stratégia); s id vypíše jednu")
    p.add_argument("analytics_id", nargs="?", help="id analytiky (bez neho sa vypíše zoznam)")
    p.add_argument("--strategy", help="len analytiky tejto stratégie")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--posudok", help="uloží posudok k tejto analytike (`@subor` číta zo súboru)")
    p.add_argument("--user", help="kto posudok napísal")
    p.set_defaults(func=cmd_analytics)

    p = sub.add_parser("prop", help="prop výzva: aká je šanca dostať sa k výplate?")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--rules", default="all",
                   help="predlohy pravidiel oddelené čiarkou, `all` (default) = všetky firmy, "
                        "`custom` = pravidlá z prepínačov nižšie; známe: "
                        + ", ".join(__import__("tester.prop", fromlist=["PRESETS"]).PRESETS))
    p.add_argument("--account", type=float, help="veľkosť účtu")
    p.add_argument("--targets", help="ciele fáz v %% oddelené čiarkou (napr. 10,5)")
    p.add_argument("--daily", type=float, help="denný limit straty v %%")
    p.add_argument("--max-loss", type=float, dest="max_loss", help="celkový limit straty v %%")
    p.add_argument("--trailing", choices=("nie", "vrchol", "koniec_dna"),
                   help="od čoho sa počíta celkový limit (default podľa predlohy)")
    p.add_argument("--day-share", type=float, dest="day_share",
                   help="pravidlo konzistencie: najlepší deň max toľko %% zisku (0 = žiadne)")
    p.add_argument("--min-days", type=int, dest="min_days", help="minimum odobchodovaných dní")
    p.add_argument("--cost", type=float, help="cena výzvy")
    p.add_argument("--payout", type=float, help="podiel zo zisku v %%")
    p.add_argument("--horizon", type=int, help="horizont v dňoch (0 = bez limitu)")
    p.add_argument("--risk", type=float, help="jedno riziko na obchod v %%; bez neho celá tabuľka")
    p.add_argument("--step", type=int, default=1, help="každý N-tý obchod ako štart pokusu")
    p.add_argument("--limit", type=int, default=40, help="najviac toľko behov (default 40)")
    p.set_defaults(func=cmd_prop)

    p = sub.add_parser("decay", help="slabne edge? posledné obdobie proti vlastnej minulosti")
    p.add_argument("query", nargs="*", help="dopyt na behy (rovnaká syntax ako `list`)")
    p.add_argument("--runs", help="konkrétne behy oddelené čiarkou (namiesto dopytu)")
    p.add_argument("--parts", type=int, default=4, help="na koľko období deliť (default 4)")
    p.add_argument("--by", choices=("time", "count"), default="time",
                   help="rovnako dlhé kalendárne úseky (default) alebo rovnako početné")
    p.add_argument("--iterations", type=int, default=2000, help="koľko vzoriek (default 2000)")
    p.add_argument("--block", type=int, default=10,
                   help="dĺžka bloku pri losovaní; 1 = nezávislé obchody (default 10)")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--limit", type=int, default=40, help="najviac toľko behov (default 40)")
    p.set_defaults(func=cmd_decay)

    p = sub.add_parser("matrix", help="ten istý profil na viacerých trhoch a TF (drží myšlienka?)")
    p.add_argument("--pairs", default="all",
                   help="`all` (default) alebo zoznam párov oddelený čiarkou")
    p.add_argument("--timeframes", default="3m",
                   help="zoznam timeframov oddelený čiarkou (default 3m)")
    p.add_argument("--goal", choices=tuple(_GOALS), default="break_even",
                   help="podľa čoho zoradiť bunky (default break-even poplatok)")
    p.add_argument("--max-dd", type=float, help="strop na max drawdown v %%")
    p.add_argument("--min-trades", type=int, default=10,
                   help="pod týmto počtom obchodov je bunka označená ako šum (default 10)")
    p.add_argument("--no-relative", dest="relative", action="store_false",
                   help="neprepočítavať prahy z absolútnych bodov na atr (závery z toho "
                        "nepatria nikam - prah v bodoch znamená na každom trhu inú vec)")
    _run_args(p)
    p.set_defaults(func=cmd_matrix, relative=True)

    p = sub.add_parser("checkup", help="základná analytika stratégie: päť okien a celá batéria meraní")
    p.add_argument("--windows", help="okná oddelené čiarkou (default päť referenčných)")
    p.add_argument("--runs", help="poskladať dokument z hotových behov namiesto nových "
                                  "(id oddelené čiarkou)")
    p.add_argument("--iterations", type=int, default=1000,
                   help="koľko náhodných behov v teste proti náhode (default 1000)")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--out", help="kam zapísať dokument (default "
                                 "tradebot/strategies/<stratégia>/docs/ANALYTIKA.md)")
    p.add_argument("--no-write", action="store_true", help="len vypísať, dokument nezapisovať")
    _run_args(p, timerange=False)
    p.set_defaults(func=cmd_checkup)

    p = sub.add_parser("matrices", help="matice z histórie; s argumentom vypíše tabuľku jednej")
    p.add_argument("matrix_id", nargs="?", help="značka matice (bez nej sa vypíše zoznam)")
    p.add_argument("--strategy", help="len matice tejto stratégie")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_matrices)

    p = sub.add_parser("hyperopt", help="hľadanie parametrov optimalizátorom (to isté zadanie ako sweep)")
    p.add_argument("--param", action="append", metavar="NAZOV=HODNOTY",
                   help="rozsah `od:do:krok` (hľadá sa v ňom spojito) alebo zoznam `a,b,c` "
                        "(hľadá sa medzi nimi); dá sa opakovať")
    p.add_argument("--suggested", action="store_true",
                   help="priestor podľa odporúčania stratégie (`hyperopt_cls.SUGGESTED`) — "
                        "to, čo na nej prežilo out-of-sample")
    p.add_argument("--goal", choices=tuple(_GOALS), default="break_even",
                   help="podľa čoho vybrať najlepšiu epochu (default break-even poplatok)")
    p.add_argument("--max-dd", type=float, help="strop na max drawdown v %%")
    p.add_argument("--min-trades", type=int, help="minimálny počet obchodov za rok, inak je epocha mimo")
    p.add_argument("--epochs", type=int, default=200,
                   help="koľko konfigurácií vyskúšať (default 200; každá je celý backtest)")
    p.add_argument("--seed", type=int, help="`--random-state` optimalizátora, na zopakovateľný beh")
    p.add_argument("--seeds", type=int,
                   help="s --remote: ten istý hyperopt s toľkými seedmi naraz (od --seed alebo 1) "
                        "a porovnanie víťazov — zhoda seedov je silnejší dôkaz než viac epoch")
    p.add_argument("--jobs", type=int, help="koľko epoch paralelne (default všetky jadrá)")
    p.add_argument("--no-verify", action="store_true",
                   help="nespúšťať víťaza na ďalších referenčných oknách (do záverov to nepatrí)")
    _run_args(p)
    p.set_defaults(func=cmd_hyperopt)

    p = sub.add_parser("hyperopts", help="hyperopty z histórie; s argumentom vypíše detail jedného")
    p.add_argument("hyperopt_id", nargs="?", help="beh hyperoptu (bez neho sa vypíše zoznam)")
    p.add_argument("--strategy", help="len hyperopty tejto stratégie")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_hyperopts)

    p = sub.add_parser("sweeps", help="mriežky z histórie; s argumentom vypíše tabuľku jednej")
    p.add_argument("sweep_id", nargs="?", help="značka mriežky (bez nej sa vypíše zoznam)")
    p.add_argument("--strategy", help="len mriežky tejto stratégie (parametre sú v každej iné)")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_sweeps)

    p = sub.add_parser("list", help="história behov, voliteľne s dopytom (rovnaká syntax ako vo webapp)")
    p.add_argument("query", nargs="*")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="detail behu")
    p.add_argument("run_id")
    p.add_argument("--json", action="store_true", help="vypíš celý záznam")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("recompute", help="prepočet peňazí uložených behov s hodnotou bodu "
                                         "(default len výpis, --write zapíše)")
    p.add_argument("--pair", help="len behy na tomto páre (napr. MNQ/USD)")
    p.add_argument("--examples", type=int, default=1, help="príkladov pred/po na pár a engine")
    p.add_argument("--write", action="store_true", help="naozaj prepísať run.json a trades.json")
    p.set_defaults(func=cmd_recompute)

    p = sub.add_parser("status", help="beží webapp, čo je vo fronte, stav gitu")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("pull", help="stiahni históriu behov z GitHubu (git pull --rebase)")
    p.set_defaults(func=cmd_pull)

    p = sub.add_parser("push", help="commitni LEN runs/, sweeps/, profiles/ a analytics/ a pushni")
    p.add_argument("--user", help="autor commitu (default TRADEBOT_USER)")
    p.set_defaults(func=cmd_push)

    p = sub.add_parser("replay", help="bod mriežky/matice/overenia (alebo beh) prehraj ako obyčajný beh do histórie")
    p.add_argument("run_id", help="id bodu z `sweeps <mriezka>`, `matrices <matica>`, `hyperopts <id>`")
    p.add_argument("--note", help="poznámka (default: odkiaľ bod je)")
    p.add_argument("--user", help="meno testera (default TRADEBOT_USER)")
    p.add_argument("--no-wait", action="store_true", help="len zaradiť do fronty webapp, nečakať")
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("chart", help="prepočítaj kresby behu do lokálnej cache grafov")
    p.add_argument("run_id")
    p.add_argument("--force", action="store_true", help="prepočítať, aj keď graf už je")
    p.set_defaults(func=cmd_chart)

    p = sub.add_parser("prune", help="odprac históriu pre git: kresby a body mriežok (bez --apply len plán)")
    p.add_argument("--apply", action="store_true",
                   help="naozaj vykonať: body prevedie do tester/sweeps/, z kresieb vyberie plan.json "
                        "a kresby aj adresáre bodov zmaže")
    p.add_argument("--keep-charts", action="store_true",
                   help="kresby nemazať, ale presunúť do lokálnej cache grafov (ostanú na disku, nie v gite)")
    p.set_defaults(func=cmd_prune)

    p = sub.add_parser("params", help="zoznam parametrov (názov, skupina, titulok, typ, rozsah)")
    p.add_argument("filter", nargs="?")
    p.add_argument("--strategy", default="ibs", help="stratégia z registry (default ibs)")
    p.set_defaults(func=cmd_params)

    return ap
