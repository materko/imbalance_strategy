"""Druhy kresieb IBS Entry Zone — tie isté čo IBS.

Zóny z FVG sa kreslia ako každá iná zóna (`Zone.boxes()`), takže vlastný druh kresby
nepotrebujú — to je presne ten zámer, aby sa značili rovnako ako SD zóny.
"""

from ..ibs.drawing import *  # noqa: F401,F403  — import zároveň druhy registruje
