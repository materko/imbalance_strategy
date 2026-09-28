"""Live telemetria zo spustených stratégií (NinjaTrader 8, MetaTrader 5) — [docs/LIVE.md](../../docs/LIVE.md).

Platforma píše JSONL spool na disk (`LiveSpool` v C# jadre), agent hubu ho číta od kurzora a
posiela na hub (`spool`, `shipper`), hub aj webapp ho ukladajú do sqlite (`store`). Sieť je
za rozhraním `transport.Transport` (dnes HTTP hubu; NATS by sa dal doplniť bez zmeny shippera
a zrkadla). Schéma udalostí je v `schema`. Nič tu nepozná stratégiu ani platformu menom — inštancia je len
adresár spoolu a `hello` riadok.
"""
