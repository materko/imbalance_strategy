"""Popisy parametrov IBS Entry Zone — parametre IBS plus zdroj zón z veľkých imbalance."""

from typing import Any

from ..ibs.params import GROUPS as IBS_GROUPS
from ..ibs.params import PARAMS as IBS_PARAMS

__all__ = ["GROUPS", "PARAMS", "FVG_GROUP"]

FVG_GROUP = "💠 Zóny z imbalance (FVG)"

#: Nová skupina ide hneď za SD zóny — je to ten istý druh zóny, len z vyššieho TF.
GROUPS: tuple[str, ...] = tuple(
    item for g in IBS_GROUPS for item in ((g, FVG_GROUP) if g == "📦 SD Zony" else (g,))
)

PARAMS: dict[str, dict[str, Any]] = {
    **IBS_PARAMS,
    "enableFvgTrading": dict(group=FVG_GROUP, title="Obchodovať zóny z imbalance",
        tooltip="Z velkych imbalance (fair value gap) na vyssich TF sa stanu obchodovatelne "
                "zony - znacia sa rovnako ako SD zony a idu tym istym modelom (STATE 0-5, "
                "imbalance / pin bar / engulfing entry). Je to presne ten isty mechanizmus, "
                "akym sa obchoduju zony zo S/R urovni a z likvidity.",
    ),
    "fvgUse5m": dict(group=FVG_GROUP, title="Brať z 5m", inline="fvgtf",
        tooltip="Hladat velke imbalance na 5-minutovom TF. Vyssi TF = menej, ale vyznamnejsich zon.",
    ),
    "fvgUse15m": dict(group=FVG_GROUP, title="15m", inline="fvgtf",
        tooltip="Hladat velke imbalance na 15-minutovom TF.",
    ),
    "fvgUse30m": dict(group=FVG_GROUP, title="30m", inline="fvgtf",
        tooltip="Hladat velke imbalance na 30-minutovom TF.",
    ),
    "fvgUse60m": dict(group=FVG_GROUP, title="1h", inline="fvgtf",
        tooltip="Hladat velke imbalance na hodinovom TF.",
    ),
    "fvgMinSize": dict(group=FVG_GROUP, title="Min. veľkosť medzery", step=0.5,
        tooltip="Ako velka musi medzera byt, aby sa z nej stala zona. Zadava sa v cenovych "
                "bodoch, ale da sa prepnut aj na ATR ci percento z ceny - to je jedina jednotka, "
                "ktora ma zmysel medzi instrumentmi. Plati pre vsetky zapnute TF naraz.",
    ),
}
