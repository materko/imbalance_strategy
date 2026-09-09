"""Freqtrade s registrovanou burzou **Tester** — inak presne to isté CLI.

    python -m tester.ftrun backtesting --config deploy/freqtrade/config.tester.json …
    python -m tester.ftrun hyperopt --hyperopt-loss IBSEdgeLoss …

### Načo to je
Burzu treba do ccxt a do Freqtradu dopísať **skôr**, než sa Freqtrade rozbehne — exchange
vzniká ešte pred načítaním stratégie, takže z nej sa registrovať nedá. Tento modul je preto
tenký obal: zaregistruje burzu (`tester.ftexchange.register`) a odovzdá riadenie
`freqtrade.main`. Všetky argumenty aj návratový kód sú Freqtradove.

Beh cez skutočnú burzu (sťahovanie dát, kontrola parity) sa nemení — vtedy sa Freqtrade
spúšťa priamo a config ukazuje na `binance`.
"""

from __future__ import annotations

import sys

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    from freqtrade.main import main as freqtrade_main

    from .ftexchange import register

    register()
    args = list(argv) if argv is not None else sys.argv[1:]
    return freqtrade_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
