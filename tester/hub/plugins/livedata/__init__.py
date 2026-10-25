"""Živé dáta na hube: sviečky a obchody stratégií naživo do feather, uzavreté mesiace raz za mesiac do gitu
a to, čo v gite ešte nie je, pre webapp (docs/DATA.md §D, docs/HUB.md „Pluginy“)."""

from .plugin import LiveData

PLUGIN = LiveData
