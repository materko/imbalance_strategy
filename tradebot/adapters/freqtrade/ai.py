"""FreqAI ako **filter nad portom**, nie namiesto neho.

### Prečo takto a nie inak
Engine je port Pine stratégie a celý jeho zmysel je, že dáva **tie isté obchody ako
TradingView** (stráži to `test_golden_tv_binance.py`). Model, ktorý by signály vytváral,
by tú paritu zrušil. Preto sa dáva **nad** engine:

1. engine nájde setup presne ako dnes — parita ostáva,
2. model k signálu predpovie, či skôr príde take profit alebo stop,
3. signály pod prahom sa preskočia a plán tých ostatných sa dá podľa istoty upraviť.

Filter je **predvolene vypnutý**. Zapnutý paritu poruší (obchodov bude menej), takže je to
rozšírenie mimo Pine — rovnako ako `minSlDistance` alebo trailing.

### Nálepka, ktorú netreba vymýšľať
Toto je jediná vec, ktorá tomuto portu vyslovene nahráva. FreqAI štandardne predpovedá
zmenu ceny o N sviečok dopredu, čo je vždy sporný cieľ. My pre **každý signál** poznáme
jeho SL aj TP z plánu, ktorý engine vypočítal — takže nálepka je „tento signál skončil na
TP" alebo „na SL". Žiadne dohady, presne to číslo, ktoré nás zaujíma.

### Prečo je príznakov len hŕstka
Máme rádovo 20–170 obchodov za rok. Model s desiatkami príznakov by sa na takej vzorke
naučil vzorku, nie trh — a to sme už raz videli pri úzkom hyperopte, ktorý skončil stratou
vo všetkých štyroch out-of-sample rokoch. Príznaky sú preto **jednotky** a sú to tie isté
veci, ktoré meria analytika (`tester.regime`): stav trhu pred vstupom a plán obchodu.
Keď sa raz ukáže, že model niečo vie, pridať sa dá; opačným smerom sa cúva ťažko.

### Čo model NEVIE zmeniť
Prah, ktorý rozhoduje, či signál **vôbec vznikne** (`minSlDistance`, štruktúrny filter,
hodiny seansy), model meniť nemôže — v čase, keď predpovedá, engine už dobehol a signál
buď je, alebo nie je. Pri takých parametroch je jediná zmysluplná odpoveď „ber / neber",
a to filter robí.

Meniť sa dá to, čo sa vzťahuje **na ten jeden obchod**: veľkosť pozície a vzdialenosť
take profitu. To je časť 2 (`AI_ADJUST`) a robí sa až v pláne obchodu, nie v engine.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["AIMixin", "TARGET", "PREDICTION_COL", "settings_of"]

#: Meno cieľa. FreqAI si stĺpce s `&` vyzdvihne samo a predikciu vráti pod tým istým menom.
TARGET = "&-tb_win"

#: Triedy nálepky. Klasifikátor FreqAI vráti pre každú z nich stĺpec s pravdepodobnosťou
#: pomenovaný presne takto — preto sú to slová, nie 1 a 0.
WIN, LOSS = "win", "loss"

#: Stĺpec, v ktorom je pravdepodobnosť, že signál skončí na take profite.
PREDICTION_COL = WIN

#: Koľko barov dopredu sa hľadá, či prišiel skôr TP alebo SL. Musí stačiť na to, ako dlho
#: obchod žije; dlhšie okno len pridá NaN riadky, kratšie by nálepku vyrobilo nesprávne.
LOOKAHEAD_BARS = 300


def settings_of(config: dict[str, Any]) -> dict[str, Any]:
    """Nastavenie AI vrstvy z configu behu. Prázdne = vypnuté."""
    return dict((config or {}).get("tradebot_ai") or {})


class AIMixin:
    """Metódy, ktoré FreqAI od stratégie čaká. Mieša sa do `TradebotStrategyBase`.

    Všetko je generické — o konkrétnej stratégii vie len toľko, čo je v dataframe po
    `populate_indicators`: signál, plán obchodu a sviečky. Nová stratégia teda AI vrstvu
    dostane bez toho, aby o nej čokoľvek písala.
    """

    # ------------------------------------------------------------------ #
    # príznaky
    # ------------------------------------------------------------------ #

    def ai_attach_plan(self, dataframe, metadata: dict):
        """Doplní `tb_*` stĺpce podľa času baru — FreqAI totiž dáva **surové sviečky**.

        Toto je jediné netriviálne miesto celej vrstvy. `populate_indicators` prežene
        engine cez celý dataframe a výsledok si nechá v runneri; FreqAI si ale pre
        tréning stavia dataframe **sám z ohlcv** a naše stĺpce v ňom nie sú. Doplnia sa
        teda spätne podľa času baru — nie prepočítaním, ktoré by mohlo dať iné čísla.

        Bar, ktorý runner nevidel, dostane NaN: bez signálu nie je ani príznak, ani
        nálepka, a FreqAI taký riadok z tréningu vyhodí.
        """
        import numpy as np

        from .base import _ts_ms
        from .runner import COLUMN_ATTRS, SignalRow

        if "tb_entry" in dataframe.columns:
            return dataframe
        runner = self._runners.get(metadata.get("pair") or "")
        if runner is None:
            for col in COLUMN_ATTRS:
                dataframe[col] = np.nan
            return dataframe
        rows = runner.rows
        prazdny = SignalRow()
        ts_index = _ts_ms(dataframe["date"])
        for col, attr in COLUMN_ATTRS.items():
            dataframe[col] = [getattr(rows.get(ts, prazdny), attr) for ts in ts_index]
        return dataframe

    def feature_engineering_expand_all(self, dataframe, period, metadata, **kwargs):
        """Zámerne prázdne.

        FreqAI sem štandardne pridáva desiatky indikátorov krát každá perióda krát každý
        timeframe. Pri stovkách nálepiek by to bol model, ktorý sa naučí vzorku. Naše
        príznaky sú v `feature_engineering_standard`, kde sa počítajú **raz**.
        """
        return dataframe

    def feature_engineering_expand_basic(self, dataframe, metadata, **kwargs):
        return dataframe

    def feature_engineering_standard(self, dataframe, metadata, **kwargs):
        """Hŕstka príznakov: stav trhu pred vstupom a plán obchodu.

        Sú to tie isté veci, ktoré meria analytika — model tak vidí ten istý svet, v akom
        sa robia závery, a keď niečo nájde, dá sa to prečítať aj bez modelu.
        """
        import numpy as np

        dataframe = self.ai_attach_plan(dataframe, metadata)
        close = dataframe["close"].astype(float)
        high, low = dataframe["high"].astype(float), dataframe["low"].astype(float)

        # -- stav trhu (to isté, čo tester/regime.py) -------------------------- #
        okno = 50
        zmena = (close - close.shift(okno)).abs()
        cesta = close.diff().abs().rolling(okno).sum()
        dataframe["%-trend"] = (zmena / cesta.replace(0, np.nan)).fillna(0.0)

        tr = np.maximum(high - low, np.maximum((high - close.shift()).abs(),
                                               (low - close.shift()).abs()))
        atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
        dataframe["%-vol"] = (atr / atr.median()).fillna(1.0)

        hi, lo = high.rolling(okno).max(), low.rolling(okno).min()
        podiel = ((close - lo) / (hi - lo).replace(0, np.nan)).fillna(0.5)
        # V smere obchodu: pre short je spodok rozsahu to isté, čo pre long vrch.
        je_short = dataframe.get("tb_enter_short", 0) == 1
        dataframe["%-pos"] = np.where(je_short, 1.0 - podiel, podiel)

        # -- plán obchodu (to, čo engine k signálu vypočítal) ------------------ #
        vstup = dataframe["tb_entry"].astype(float)
        sl = dataframe["tb_sl"].astype(float)
        tp = dataframe["tb_tp"].astype(float)
        vzdialenost = (vstup - sl).abs()
        dataframe["%-sl_pct"] = (vzdialenost / vstup.replace(0, np.nan) * 100).fillna(0.0)
        dataframe["%-rr"] = ((tp - vstup).abs() / vzdialenost.replace(0, np.nan)).fillna(0.0)

        # -- kedy a ktorým smerom --------------------------------------------- #
        dataframe["%-hour"] = dataframe["date"].dt.hour
        dataframe["%-short"] = je_short.astype(int)
        return dataframe

    # ------------------------------------------------------------------ #
    # nálepka
    # ------------------------------------------------------------------ #

    def set_freqai_targets(self, dataframe, metadata, **kwargs):
        """`win` = signál skončil na take profite, `loss` = na stope, `NaN` = žiadny signál.

        Hľadá sa dopredu, ktorá úroveň príde skôr. Je to pohľad do budúcnosti, ale
        **len pri tréningu** — presne na to je `set_freqai_targets`; FreqAI trénuje na
        minulom okne a predpovedá na nasledujúcom, takže sa to do rozhodnutia nedostane.

        Bary bez signálu ostávajú `NaN` a FreqAI ich z tréningu vyhodí. Model sa teda učí
        len na tom, čo engine naozaj ponúkol — nie na každom bare grafu.
        """
        import numpy as np

        dataframe = self.ai_attach_plan(dataframe, metadata)
        n = len(dataframe)
        vysledok = np.full(n, np.nan, dtype=object)
        vstup = dataframe["tb_entry"].to_numpy(dtype=float)
        sl = dataframe["tb_sl"].to_numpy(dtype=float)
        tp = dataframe["tb_tp"].to_numpy(dtype=float)
        high = dataframe["high"].to_numpy(dtype=float)
        low = dataframe["low"].to_numpy(dtype=float)
        je_long = (dataframe.get("tb_enter_long", 0) == 1).to_numpy()
        je_short = (dataframe.get("tb_enter_short", 0) == 1).to_numpy()

        for i in np.flatnonzero(je_long | je_short):
            if not (np.isfinite(sl[i]) and np.isfinite(tp[i]) and np.isfinite(vstup[i])):
                continue
            koniec = min(i + 1 + LOOKAHEAD_BARS, n)
            h, l = high[i + 1:koniec], low[i + 1:koniec]
            if je_long[i]:
                tp_kedy = np.argmax(h >= tp[i]) if (h >= tp[i]).any() else -1
                sl_kedy = np.argmax(l <= sl[i]) if (l <= sl[i]).any() else -1
            else:
                tp_kedy = np.argmax(l <= tp[i]) if (l <= tp[i]).any() else -1
                sl_kedy = np.argmax(h >= sl[i]) if (h >= sl[i]).any() else -1
            if tp_kedy < 0 and sl_kedy < 0:
                continue                      # do konca okna sa nestalo nič — bez nálepky
            if sl_kedy < 0:
                vysledok[i] = WIN
            elif tp_kedy < 0:
                vysledok[i] = LOSS
            else:
                # Rovnaký bar sa počíta ako stop: v jednom bare nevieme, čo prišlo skôr,
                # a optimistický odhad by model naučil, že sporné obchody vychádzajú.
                vysledok[i] = WIN if tp_kedy < sl_kedy else LOSS

        dataframe[TARGET] = vysledok
        return dataframe

    # ------------------------------------------------------------------ #
    # 1. brať signál, alebo nie
    # ------------------------------------------------------------------ #

    def ai_gate(self, dataframe, pair: str):
        """Zahodí signály, ktorým model neverí. Vracia dataframe a počet zahodených.

        Bez zapnutej AI vrstvy alebo bez predikcie sa nemení nič — parita s Pine tak
        ostáva presne tam, kde bola.
        """
        import numpy as np

        nastavenie = settings_of(getattr(self, "config", {}))
        prah = float(nastavenie.get("min_probability") or 0.0)
        if prah <= 0 or PREDICTION_COL not in dataframe.columns:
            return dataframe, 0

        p = dataframe[PREDICTION_COL].astype(float)
        # `do_predict` je 1 len tam, kde model naozaj predpovedal (nie mimo tréningu
        # a nie na odľahlých dátach). Inde sa signál nechá tak, ako je — model, ktorý
        # nevie, nemá právo vetovať.
        vie = dataframe["do_predict"] == 1 if "do_predict" in dataframe.columns else True
        signal = (dataframe.get("tb_enter_long", 0) == 1) | (dataframe.get("tb_enter_short", 0) == 1)
        zahodit = signal & vie & (p.fillna(1.0) < prah)

        pocet = int(zahodit.sum())
        if pocet:
            dataframe.loc[zahodit, "tb_enter_long"] = 0
            dataframe.loc[zahodit, "tb_enter_short"] = 0
            logger.info("%s %s: AI filter zahodil %d z %d signalov (prah %.2f)",
                        getattr(self, "spec", None) and self.spec.key, pair, pocet,
                        int(signal.sum()), prah)
        return dataframe, pocet

    # ------------------------------------------------------------------ #
    # 2. zmena vybraných parametrov podľa istoty
    # ------------------------------------------------------------------ #

    def ai_confidence(self, pair: str, signal_ts: int) -> float | None:
        """Istota modelu pre signál z daného baru, alebo `None`, keď ju nemá."""
        nastavenie = settings_of(getattr(self, "config", {}))
        if not nastavenie.get("adjust"):
            return None
        df = getattr(self, "_ai_predictions", {}).get(pair)
        if df is None:
            return None
        return df.get(signal_ts)

    def ai_scale(self, pair: str, signal_ts: int, kluc: str) -> float:
        """Násobok pre `kluc` (`size`, `rr`) podľa istoty modelu; 1.0 = nemeniť.

        Mapovanie je zámerne lineárne a s mantinelmi zo zadania behu: istota pod
        `min_probability` obchod ani nevznikne (rieši to filter), takže sa škáluje len
        v pásme nad prahom. Model tak nemôže poslať veľkosť do neba ani na nulu.
        """
        nastavenie = settings_of(getattr(self, "config", {}))
        rozsah = (nastavenie.get("adjust") or {}).get(kluc)
        if not rozsah:
            return 1.0
        istota = self.ai_confidence(pair, signal_ts)
        if istota is None:
            return 1.0
        prah = float(nastavenie.get("min_probability") or 0.0)
        podiel = 0.0 if istota <= prah else min(1.0, (istota - prah) / max(1e-9, 1.0 - prah))
        nizky, vysoky = float(rozsah[0]), float(rozsah[1])
        return nizky + (vysoky - nizky) * podiel

    def ai_remember(self, pair: str, dataframe) -> None:
        """Odloží predikcie podľa času baru — plán obchodu ich potrebuje neskôr."""
        if PREDICTION_COL not in dataframe.columns:
            return
        from .base import _ts_ms

        if not hasattr(self, "_ai_predictions"):
            self._ai_predictions = {}
        self._ai_predictions[pair] = dict(zip(_ts_ms(dataframe["date"]),
                                              dataframe[PREDICTION_COL].astype(float)))
