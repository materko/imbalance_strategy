"""Metadáta IBS Entry Zone pre webapp — vrstvy grafu a závislosti prepínačov.

Vrstvy sú zhodné s IBS: zóny z FVG sa kreslia ako každá iná zóna, takže patria do
existujúcej vrstvy „SD zóny" — o to presne ide, nech sa značia rovnako.
"""

from ..ibs.meta import FEATURES as IBS_FEATURES
from ..ibs.meta import INERT_INPUTS, KIND_TITLES, LAYERS
from ..ibs.meta import PARAM_NOTES as IBS_PARAM_NOTES

__all__ = ["FEATURES", "INERT_INPUTS", "KIND_TITLES", "LAYERS", "PARAM_NOTES"]

#: Prepínače, ktoré zapínajú ďalšie polia — formulár podľa toho polia zašedne.
FEATURES = list(IBS_FEATURES) + [
    {"switches": ["enableFvgTrading", "enableIfvgTrading"],
     "params": ["fvgUse5m", "fvgUse15m", "fvgUse30m", "fvgUse60m", "fvgMinSize"]},
]

PARAM_NOTES = {**IBS_PARAM_NOTES}
