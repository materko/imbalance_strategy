"""Most do C# jadra — stratégia napísaná v C# sa zvyšku TradeBota javí ako Python engine.

Toto je „Freqtrade adaptér nad C# jadrom": generický `TradebotStrategyBase` (a rovnako
emulátor MultiCharts, webapp, analytika) volá `Engine.on_bar`, a `CSharpEngine` to volanie
odovzdá C# triede z `csharp/` — v procese cez pythonnet alebo cez `TradeBot.Host.exe`.

    build.py    preklad `csharp/` -> `csharp/bin/TradeBot.dll` (csc z .NET Frameworku / Mono)
    bridge.py   transport (pythonnet | stdio), jeden JSON protokol
    engine.py   `CSharpEngine` + `csharp_engine_factory(kľúč)` pre `StrategySpec.engine_factory`
"""

__all__ = ["CSharpEngine", "CSharpEngineOutput", "csharp_engine_factory"]


def __getattr__(name: str):
    # lenivo: `python -m tradebot.adapters.csharp.build` nemá ťahať engine (a s ním seba samého)
    if name in __all__:
        from . import engine

        return getattr(engine, name)
    raise AttributeError(name)
