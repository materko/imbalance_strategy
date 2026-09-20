"""pythonnet (CLR v procese Pythonu) — aby koniec procesu netrval minúty.

`pythonnet.load()` si na koniec procesu zaregistruje `unload` a ten pred vypnutím CLR opakovane
prejde celú haldu Pythonu (`gc.collect`). V malom procese si to nikto nevšimne; po Freqtrade
backteste (milióny objektov) to bolo ~20 s a po celej sade testov (90 miliónov objektov, jeden
zber 10 s) **~15 minút** „visiaceho" procesu po vypísaní výsledku. Vynechať `unload` nejde —
CLR potom pri konci procesu spadne na GIL a proces vráti kód 127.

`tame_shutdown()` preto `unload` nahradí verziou, ktorá tesne pred ním zavolá `gc.freeze()`:
všetko živé sa presunie do trvalej generácie, ktorú zber neprechádza, a `unload` je hotový za
stotiny sekundy. Volá sa po KAŽDOM načítaní CLR — cez most `tradebot.adapters.csharp` aj cez
`import clr` v MultiCharts adaptéri —, lebo nie je dané, kto ho načíta prvý. Je idempotentná
a bez pythonnet nerobí nič. Modul je v jadre, lebo ho potrebujú dva adaptéry; sám nič .NET neimportuje.
"""

from __future__ import annotations

import atexit
import gc
import sys

__all__ = ["tame_shutdown"]


def _fast_unload() -> None:
    pythonnet = sys.modules.get("pythonnet")
    if pythonnet is None:
        return
    gc.freeze()
    pythonnet.unload()


def tame_shutdown() -> None:
    """Zavolaj po načítaní CLR (pythonnet.load / import clr). Bezpečné volať opakovane."""
    pythonnet = sys.modules.get("pythonnet")
    if pythonnet is None or not hasattr(pythonnet, "unload"):
        return  # MultiCharts x Python má vlastné `clr`, nie pythonnet z pip
    atexit.unregister(pythonnet.unload)
    atexit.unregister(_fast_unload)
    atexit.register(_fast_unload)
