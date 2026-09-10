"""Čo o ladení vie **stratégia** — a čo si generický hyperopt vyzdvihne z registry.

Typy a rozsahy parametrov generická časť (`tradebot.adapters.freqtrade.hyperplan`) nikde
nedrží: číta ich z configu stratégie (`CONSTRAINTS`, `SIZE_FIELDS`, `ENUM_FIELDS`, typy
dataclass polí), takže sa nemá ako rozísť s tým, čo config prijme. To je generické
a nová stratégia pre to nemusí napísať nič.

Sú ale tri veci, ktoré z configu vyčítať **nejde**, a tie sú vlastné každej stratégii:

1. **Čo sa oplatí ladiť.** Config povie, že `rrRatio` je float 0,5–10. Nepovie, že práve
   `rrRatio`, `slLookback` a `structureSwingLen` boli jediné, ktoré na IBS prežili päť
   rokov, kým desať prahov v jednotke `atr` dalo +34,8 % na ladenom roku a stratu vo
   všetkých štyroch out-of-sample rokoch.
2. **Pred čím varovať.** To isté meranie, len z druhej strany: parametre, ktoré vyzerajú
   ako lákavá páka a v skutočnosti sa na nich hyperopt prefituje.
3. **Väzby medzi parametrami.** Hyperopt vzťah „koniec okna musí byť za začiatkom"
   vyjadriť nevie — vyberá každý parameter zvlášť. Bez opravy by celá vetva priestoru
   dávala nula obchodov a optimalizátor by v nej blúdil naslepo.

Stratégia to preto zabalí do podtriedy `StrategyHyperopt` vo vlastnom module
(`tradebot/strategies/<key>/hyperopt.py`) a pripojí ju do registry ako `hyperopt_cls`.
Generická časť ju nepozná menom — vyzdvihne si ju cez `StrategySpec`. Stratégia, ktorá
triedu nedá, sa ladiť dá tiež: platí základ tejto triedy, teda „nič neodporúčam, pred
ničím nevarujem, žiadne väzby".

Modul je zámerne bez závislostí (žiadny Freqtrade, žiadne pandas) — importuje ho registry,
ktorú načítava aj MultiCharts a webapp.
"""

from __future__ import annotations

from typing import Any, ClassVar

__all__ = ["StrategyHyperopt", "Suggestion"]

#: Odporúčaný rozsah jedného parametra: `{"low":…, "high":…, "step":…}` alebo
#: `{"choices": [...]}` — presne tvar, aký prijíma plán (`hyperplan.Plan`).
Suggestion = dict[str, Any]


class StrategyHyperopt:
    """Vedomosti stratégie o ladení. Bez prepísania je to „neviem nič", nie zákaz."""


    #: Čo z **plánu obchodu** smie AI meniť podľa svojej istoty: kľúč → (parameter
    #: configu, ktorý to isté robí staticky; opis). Kľúče sú tri, lebo toľko vecí sa
    #: k jednému obchodu vzťahuje — všetko ostatné rozhoduje, či signál **vôbec vznikne**,
    #: a to sa v čase predikcie už stalo. Tam je jediná zmysluplná odpoveď „ber / neber",
    #: a to robí filter.
    #:
    #: Stratégia môže zoznam rozšíriť alebo doplniť, ktorý jej parameter ktorému kľúču
    #: zodpovedá — vo výpise je to potom vidieť.
    AI_ADJUSTABLE: dict[str, tuple[str, str]] = {
        "size": ("", "veľkosť pozície — koľko sa na obchod stavia"),
        "tp": ("", "vzdialenosť take profitu od vstupu (teda odmena za to isté riziko)"),
        "sl": ("", "vzdialenosť stopu; veľkosť sa dopočíta tak, aby riziko na obchod "
                   "ostalo rovnaké"),
    }

    @classmethod
    def ai_adjustable(cls) -> dict[str, tuple[str, str]]:
        """Kľúče, ktoré táto stratégia dovolí meniť modelu."""
        return dict(cls.AI_ADJUSTABLE)

    #: Parametre, ktoré sa na tejto stratégii oplatí ladiť, s rozsahmi. Poradie je
    #: poradie ponuky vo webapp — najsilnejšia páka prvá.
    SUGGESTED: ClassVar[dict[str, Suggestion]] = {}

    #: `parameter -> prečo naň pozor`. Nie zákaz: tester ho smie ladiť, ale má vedieť,
    #: čo sa stalo, keď sa to skúsilo naposledy.
    WARN: ClassVar[dict[str, str]] = {}

    #: Krátka veta do formulára — čo o ladení tejto stratégie vieme.
    NOTE: ClassVar[str] = ""

    #: `vlastnosť obchodu -> parameter configu, ktorý ju riadi`. Vďaka tomu analytika
    #: (`tester.analytics`) nekončí zistením „tesné stopy nezarábajú", ale odkazom na
    #: parameter, ktorý sa tým dá zmeniť — a ten sa dá rovno preladiť.
    FEATURE_PARAMS: ClassVar[dict[str, str]] = {}

    @classmethod
    def constrain(cls, cfg: Any) -> None:
        """Opraví väzby medzi parametrami po vložení hodnôt epochy do configu.

        Beží po každej epoche, na už nastavenom configu. Hyperopt vyberá parametre
        nezávisle, takže sa tu naprávajú kombinácie, ktoré by boli nezmyselné —
        nie preto, aby sa priestor zúžil, ale aby v ňom nebola diera bez obchodov.
        """

    @classmethod
    def suggested_plan(cls, names: list[str] | None = None) -> dict[str, Suggestion]:
        """Odporúčané rozsahy pre vybrané parametre (bez argumentu všetky odporúčané)."""
        if names is None:
            return {k: dict(v) for k, v in cls.SUGGESTED.items()}
        return {n: dict(cls.SUGGESTED[n]) for n in names if n in cls.SUGGESTED}
