"""Čo o ladení IBS Entry Zone vieme — základ z IBS plus parametre vrstvy FVG."""

from ..ibs.hyperopt import IBSHyperopt

__all__ = ["IBSEntryZoneHyperopt"]


class IBSEntryZoneHyperopt(IBSHyperopt):
    """Vrstva FVG pridáva parametre, ktoré sa oplatí ladiť spolu s prahmi zón."""
