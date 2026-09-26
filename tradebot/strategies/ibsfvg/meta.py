"""Metadáta IBS FVG + IFVG pre webapp — IBS Entry Zone bez S/R, likvidity a Elliotta.

Tieto tri vrstvy stratégia nepoužíva: zóny vznikajú len z FVG a IFVG. Polia ostávajú
v configu (engine IBS ich číta), ale sú natvrdo vypnuté (`IBSFvgConfig`) a formulár ich
neukazuje — `REMOVED_INPUTS`.
"""

from ..ibsentry.meta import FEATURES as _ENTRY_FEATURES
from ..ibsentry.meta import INERT_INPUTS, KIND_TITLES, LAYERS, PARAM_NOTES
from ..ibsentry.params import PARAMS as _ENTRY_PARAMS

__all__ = ["FEATURES", "INERT_INPUTS", "KIND_TITLES", "LAYERS", "PARAM_NOTES", "REMOVED_INPUTS", "REMOVED_GROUPS"]

#: Skupiny formulára, ktoré stratégia vôbec nemá.
REMOVED_GROUPS = ("📏 Support/Resistance", "💧 Likvidita (Sweep)", "🌊 Elliott Waves")

#: Celé skupiny S/R, likvidity a Elliotta plus prepínače obchodovania z S/R a likvidity.
REMOVED_INPUTS: frozenset[str] = frozenset(
    {name for name, meta in _ENTRY_PARAMS.items() if meta.get("group") in REMOVED_GROUPS}
    | {"enableSrTrading", "enableLqTrading"}
)

FEATURES = [
    f for f in _ENTRY_FEATURES
    if not set(f.get("switches", ())) <= REMOVED_INPUTS and not set(f.get("params", ())) <= REMOVED_INPUTS
]
