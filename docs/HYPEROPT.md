# Hyperopt: hľadanie parametrov bez písania kódu

Hyperopt skúša konfigurácie a učí sa z odpovedí. Sweep prejde mriežku, ktorú vypíšeš;
hyperopt hľadá v rozsahu, ktorý mu dáš. **Zadanie je pre oboje rovnaké** — tie isté
`--param`, tie isté kritériá aj mantinely — takže sa tester rozhoduje až na konci, čo sa
má s hodnotami stať.

| | sweep | hyperopt |
|---|---|---|
| čo urobí | prejde všetky body | hľadá v rozsahu, učí sa |
| koľko behov | presne koľko bodov | koľko epoch zadáš |
| `2:8:0.5` | 13 hodnôt | spojito medzi 2 a 8, po desatinách |
| `3,5,8` | 3 hodnoty | 3 možnosti (aj tu) |
| v histórii | každý bod ako beh | víťaz na 5 oknách, epochy v `.fthypt` |
| kedy | 1–2 parametre, chcem vidieť tvar | 3 a viac parametrov |

```bash
PY -m tester.webapp.cli hyperopt --param rrRatio=2:8:0.5 --param slLookback=5:40:1 \
   --profile docs/profily_archiv/ibs/btcusdt_3m_binance_ny_sl_risk1.json \
   --timerange 20250904-20260904 --goal break_even --min-trades 15 --epochs 200
```

Kritériá sú tie isté štyri ako pri sweepe (`break_even`, `profit`, `winrate`, `drawdown`)
a k nim `--max-dd` a `--min-trades` — [tester/AI_TESTING.md §7](../tester/AI_TESTING.md).
Mantinely nie sú zákaz, ale penalizácia rastúca so vzdialenosťou od limitu: plochá stena
je pre optimalizátor slepá, nevidí, ktorým smerom sa má vydať.

## Overenie na ďalších oknách nie je doplnok

Hyperopt nájde optimum **toho okna, ktoré videl**. To nie je to isté ako dobrá stratégia.
Prvá verzia priestoru ladila desať prahov v jednotke `atr` a víťazná epocha mala na
ladenom roku +34,8 %, kým **všetky štyri** ostatné roky boli stratové (−11 % až −65 %) —
[docs/merania/HYPEROPT_btcusdt_2026-09-04.md](merania/HYPEROPT_btcusdt_2026-09-04.md).

Preto `hyperopt` po dobehnutí pustí víťazné parametre ako obyčajné backtesty na piatich
referenčných oknách a povie jednu vetu:

```
[1/5] 20250904-20260904   done  obchodov 20  PnL 21.067 %  break-even 0.2428 % (ladene)
[2/5] 20211001-20221001   done  obchodov 27  PnL  5.885 %  break-even 0.0917 %
...
VITAZ PREZIL: break-even je kladny vo vsetkych 4 oknach mimo ladeneho.
```

Verdikt pozerá **znamienko po oknách, nie súčet**. `PRETRENOVANE` znamená, že parametre
netreba ani ukladať. Preskočiť sa to dá (`--no-verify`), ale do záverov taký výsledok
nepatrí.

Overovacie behy sú obyčajné behy v histórii so značkou `hyperopt`, takže sa dajú otvoriť,
porovnať aj prehnať Monte Carlom — rovnako ako body sweepu.

## Odkiaľ sa berú hranice

Poradie je: **čo napíšeš** → **čo odporučí stratégia** → **čo dovolí Pine**.

1. **Text v zadaní.** `rrRatio=2:8:0.5` je rozsah 2–8 s presnosťou na desatiny.
   `slLookback=10,20,30` je vypísaný zoznam — keď hodnoty vymenuješ, iné číslo nechceš
   a hyperopt to vyjadriť vie.
2. **Vynechaný rozsah** znamená celý povolený: `--param slLookback=` vezme hranice
   z `CONSTRAINTS` configu stratégie, teda z Pine.
3. **Pine rozsah je strop.** Hranica mimo neho sa odmietne s hláškou — `rrRatio` nad 10
   by config aj tak neprijal a beh by spadol až v strede ladenia.

Typ parametra sa nikde nepíše druhýkrát: berie sa z polí configu (`int`, `float`, `bool`,
`SizeSpec`, enum), takže sa nemá ako rozísť s tým, čo config prijme. Veľkostné pole si
drží jednotku — `minSlDistance=0.1@pct,0.5@pct` ladí číslo, `pct` je pevné. Bez jednotky
sa vezme predvolená jednotka poľa.

**Krok pri hyperopte znamená presnosť, nie mriežku.** `DecimalParameter` inú mriežku než
desatinné miesta nevie: `2:8:0.5` a `2:8:0.1` sa líšia len tým, na koľko miest sa hodnota
zaokrúhli. Kto chce presne dané hodnoty, patrí na sweep — alebo ich vypíše zoznamom.

## Ako pridať hyperopt k novej stratégii

Nič robiť **nemusíš**. Typy a rozsahy si generická časť prečíta z configu, takže hyperopt
funguje na každej registrovanej stratégii hneď. Sú ale tri veci, ktoré z configu vyčítať
nejde, a tie stratégia povedať vie:

1. **Čo sa oplatí ladiť.** Config povie, že `rrRatio` je float 0,5–10. Nepovie, že práve
   `rrRatio`, `slLookback` a `structureSwingLen` boli jediné, ktoré na IBS prežili päť
   rokov.
2. **Pred čím varovať.** To isté z druhej strany: parametre, ktoré vyzerajú ako lákavá
   páka a v skutočnosti sa na nich hyperopt prefituje.
3. **Väzby medzi parametrami.** Hyperopt vzťah „koniec okna musí byť za začiatkom"
   vyjadriť nevie — každý parameter vyberá zvlášť. Bez opravy by polovica kombinácií
   dávala okno nulovej dĺžky, teda vetvu priestoru bez jediného obchodu, v ktorej
   optimalizátor blúdi naslepo.

Zapíše sa to do `tradebot/strategies/<key>/hyperopt.py`:

```python
"""Čo o ladení <stratégie> vieme — odporúčania, varovania a väzby."""

from __future__ import annotations

from typing import ClassVar

from ..hyperopt import StrategyHyperopt, Suggestion


class MojaHyperopt(StrategyHyperopt):
    #: Veta do formulára — čo o ladení tejto stratégie vieme.
    NOTE: ClassVar[str] = "Menej je viac: prežili len zmeny s jedným stupňom voľnosti."

    #: Ponuka vo formulári, v tomto poradí. Rozsah v tom istom tvare ako plán.
    SUGGESTED: ClassVar[dict[str, Suggestion]] = {
        "rrRatio": {"low": 2.0, "high": 8.0, "step": 0.5},
        "slLookback": {"low": 5, "high": 40},
        "useStructureFilter": {"choices": [False, True]},
        # veľkostné pole: v `pct`, nie v cenových bodoch — inak neplatí na inom trhu
        "minSlDistance": {"low": 0.0, "high": 0.6, "step": 0.05, "unit": "pct"},
    }

    #: `parameter -> prečo naň pozor`. Nie zákaz — tester ho smie ladiť.
    WARN: ClassVar[dict[str, str]] = {
        "minImbSizePoints": "prah v cenových bodoch; prefitoval sa — ak už, tak v jednotke atr",
    }

    @classmethod
    def constrain(cls, cfg) -> None:
        """Väzby medzi parametrami po vložení hodnôt epochy."""
        if cfg.sess2TradeEndH <= cfg.sess2TradeStartH:
            cfg.sess2TradeEndH = min(int(cfg.sess2TradeStartH) + 1, 23)
```

a pripojí do registry v `tradebot/strategies/<key>/__init__.py`:

```python
SPEC = StrategySpec(
    ...
    hyperopt_cls=MojaHyperopt,
)
```

To je celé. Generická časť si triedu vyzdvihne cez `hyperplan.knowledge(spec)`, menom
žiadnu stratégiu nepozná (stráži to test) a stratégia bez triedy sa ladí tiež — len nič
neodporúča a pred ničím nevaruje.

**Ako nastaviť hranice v `SUGGESTED`:**

| pole | kedy | príklad |
|---|---|---|
| `low`, `high` | číselný parameter | `{"low": 2.0, "high": 8.0}` |
| `step` | presnosť (počet desatinných miest) | `{"step": 0.5}` → jedno miesto |
| `choices` | prepínač, enum, alebo vymenované čísla | `{"choices": [False, True]}` |
| `unit` | veľkostné pole (`abs`, `ticks`, `atr`, `pct`) | `{"unit": "pct"}` |

Hranice drž **užšie**, než dovoľuje Pine, a odôvodni ich meraním. Široký rozsah nie je
štedrosť — je to viac miesta na prefitovanie. A prahy zadávaj v `atr` alebo `pct`, nie
v cenových bodoch: bod na NAS100 a bod na EURUSD nie je to isté a rozsah v bodoch prestane
platiť pri prvej zmene páru.

## Ako to funguje vnútri

Freqtrade zisťuje, čo má ladiť, tak, že si po triede stratégie prejde atribúty a hľadá
v nich `IntParameter`/`DecimalParameter`/`CategoricalParameter`. Priestor je teda normálne
súčasť kódu — a tester, ktorý kód nepíše, si ho nemá ako zvoliť.

Plán ten krok obchádza: je to JSON, cesta k nemu je v `TRADEBOT_HYPEROPT_PLAN` a
`TradebotStrategyBase.__init_subclass__` z neho **pri importe triedy** dorobí tie isté
objekty a prilepí ich na triedu. Freqtrade medzi „napísané v kóde" a „prilepené pri
importe" nerozlišuje, lebo sa pozerá až na hotovú triedu.

```json
{
  "strategy": "ibs",
  "goal": "winrate", "max_dd": 15.0, "min_trades": 20,
  "knobs": {
    "rrRatio":    {"low": 2, "high": 6, "step": 0.5},
    "slLookback": {"low": 5, "high": 40}
  }
}
```

Priestor má vlastné meno **`plan`** (nie `buy`/`sell`), takže `--spaces plan` ladí presne
to, čo tester navolil. Kritérium a mantinely nesie ten istý plán a číta ich loss funkcia
`TradebotPlanLoss` — zadanie je na jednom mieste a nemôže sa rozísť.

Dve veci, ktoré musia byť dodržané a ľahko sa na ne zabudne:

- **`--analyze-per-epoch` je povinné.** Freqtrade počíta `populate_indicators` raz pre
  celý beh a per-epochu prepočítava len `populate_entry_trend`, lebo predpokladá, že
  priestor „buy" ovplyvňuje iba signály. Celý náš engine beží v `populate_indicators`,
  takže bez toho prepínača dá **každá epocha ten istý výsledok** (prejaví sa to tak, že
  všetkých N epoch má identický PnL aj počet obchodov).
- **Runner sa musí postaviť nanovo.** `EngineRunner` je inkrementálny a drží stav; je
  preto cachovaný podľa odtlačku configu, aby epocha nepočítala so starými parametrami.

## Prečo hyperopt nie je odpoveď na všetko

Sweep je hlúpejší, ale čitateľný: „RR 3 → 5 zlepší break-even vo všetkých oknách" je
záver, s ktorým sa dá pracovať, kým „optimalizátor našiel 7,3" nie. A nemá ako pretrénovať
viac, než koľko bodov mriežka má. Na jeden–dva parametre preto radšej sweep; hyperopt sa
oplatí od troch.

---

# FreqAI: dá sa pripojiť, ale odpovedá na inú otázku

**Áno, technicky sa dá** — FreqAI je súčasť tej istej inštalácie Freqtradu a Tester ním
beží cez rovnaký obal (`tester.ftrun`). Nie je to ale „hyperopt, len lepší": hyperopt
vyberie **statické parametre**, s ktorými sa potom obchoduje. FreqAI trénuje **model,
ktorý sa v čase mení** — v každom okne sa pretrénuje na poslednom kuse histórie. To je
iná vec a inak sa aj vyhodnocuje.

## Čo by to znamenalo pre náš port

Náš engine je port Pine stratégie a celý zmysel má v tom, že dáva **tie isté obchody ako
TradingView** (stráži to `test_golden_tv_binance.py`). Model, ktorý by signály vytváral,
by paritu zrušil. Zmysluplné miesto pre FreqAI je preto **filter nad portom**, nie
namiesto neho:

1. Engine vygeneruje signál presne ako dnes (parita ostáva).
2. Model k signálu predpovie, či skôr dosiahne TP alebo SL.
3. Signály pod prahom pravdepodobnosti sa preskočia.

Tým sa parita **poruší** (obchodov bude menej), takže by to muselo byť rozšírenie mimo
Pine s defaultom „vypnuté" a v `PORT_ONLY_FIELDS` — presne tak, ako sú riešené ostatné
rozšírenia portu (`minSlDistance`, trailing).

Na tomto porte je jedna vec, ktorá FreqAI vyslovene nahráva: **cieľ sa dá označiť presne.**
FreqAI štandardne predpovedá zmenu ceny o N sviečok dopredu, čo je vždy sporný cieľ. My ale
pre každý signál poznáme jeho SL aj TP z plánu obchodu, takže sa dá spätne vyrobiť čistá
nálepka „tento signál skončil na TP / na SL" (`extreme_before_stop` to už počíta). To je
supervised label bez dohadov — a je to presne to číslo, ktoré nás zaujíma.

## Čo treba dorobiť

| krok | čo to je |
|---|---|
| závislosti | `pip install "freqtrade[freqai]"` — pridá `datasieve`, `lightgbm`, `xgboost`, `scikit-learn`, `tensorboard` (dnes nie sú a `freqtrade.freqai` sa bez nich ani nenaimportuje) |
| sekcia configu | `freqai` blok: `train_period_days`, `backtest_period_days`, `identifier`, `feature_parameters` (`include_timeframes`, `indicator_periods_candles`, `include_shifted_candles`), `data_split_parameters` |
| metódy stratégie | `feature_engineering_expand_all`, `feature_engineering_expand_basic`, `feature_engineering_standard`, `set_freqai_targets` — v adaptéri, generické; príznaky by mali byť to, čo engine aj tak počíta (vzdialenosť k zóne, veľkosť imbalance, ATR, fáza STATE, seansa) |
| nálepka | `set_freqai_targets` označí bary so signálom podľa toho, či sa dosiahol TP pred SL; bary bez signálu ostanú `NaN` (FreqAI ich vyhodí) |
| prah v configu stratégie | `aiMinProbability` ako port-only pole, default 0 = filter vypnutý, parita zachovaná |
| spustenie | `--freqaimodel LightGBMClassifier` a `--strategy` ako dnes |

## Čo za to zaplatíme

- **Beh sa spomalí rádovo.** FreqAI trénuje walk-forward: pri `backtest_period_days: 7`
  je to ~52 tréningov na rok navrch k backtestu, ktorý dnes trvá 20–40 s.
- **Výsledok prestane byť determinovaný.** Golden testy musia zostať mimo FreqAI a
  porovnanie s TradingView aj s MultiCharts platí len pre vetvu s vypnutým filtrom.
- **Málo obchodov.** Toto je hlavný problém a netreba naň dlho čakať: máme ~20–170
  obchodov za rok, teda ~100–800 nálepiek za päť rokov. Na model s desiatkami príznakov
  je to veľmi málo a prefitovanie hrozí ešte viac než pri hyperopte s desiatimi prahmi —
  a to skončilo stratou vo všetkých štyroch out-of-sample rokoch. Príznaky by preto museli
  byť **rádovo jednotky**, nie desiatky, a hodnotiť by sa to muselo na tých istých piatich
  oknách so znamienkom po rokoch.

## Odporúčanie

Poradie prác, nie zákaz:

1. **Najprv dotiahnuť hyperopt** (webapp, história, poriadne merania na piatich oknách).
   Vieme z neho čítať, je determinovaný a lacný.
2. **Potom zmerať, či má filter vôbec priestor.** Nie modelom — ručne. Rozdeliť existujúce
   obchody podľa vlastností, ktoré engine už počíta (vzdialenosť k zóne, veľkosť
   imbalance, ATR, seansa, fáza STATE), a pozrieť, či niektorá skupina má systematicky
   horší break-even. Ak áno, filter má čo zlepšovať a FreqAI je na to legitímny nástroj.
   Ak nie, model nemá čo nájsť a ušetríme si ho.
3. **FreqAI až vtedy** — a rovno ako port-only filter s defaultom „vypnuté".

Ten druhý krok je pár hodín práce nad dátami, ktoré už v `tester/runs/` máme, a odpovie na
otázku, ktorú by inak FreqAI zodpovedal drahšie a menej čitateľne.
