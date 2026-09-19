// Zakladne datove typy jadra - zrkadlo `tradebot/core/types.py`.
// Nic v jadre nesmie poznat NinjaTrader ani Freqtrade: jadro je platformovo neutralne.
using System;
using System.Collections.Generic;

namespace TradeBot.Core
{
    /// <summary>Jedna sviecka. `Time` je cas OTVORENIA baru v ms epoch UTC (ako Pine `time`).</summary>
    public sealed class Bar
    {
        public readonly long Time;
        public readonly double Open;
        public readonly double High;
        public readonly double Low;
        public readonly double Close;
        public readonly double Volume;

        public Bar(long time, double open, double high, double low, double close, double volume)
        {
            Time = time; Open = open; High = high; Low = low; Close = close; Volume = volume;
        }

        public double BodyTop { get { return Math.Max(Open, Close); } }
        public double BodyBottom { get { return Math.Min(Open, Close); } }
        public double Range { get { return High - Low; } }
        public bool IsUp { get { return Close >= Open; } }

        public static Bar FromJson(Dictionary<string, object> d)
        {
            return new Bar(Json.ToLong(d["t"]), Json.ToDouble(d["o"]), Json.ToDouble(d["h"]),
                           Json.ToDouble(d["l"]), Json.ToDouble(d["c"]), Json.ToDouble(d["v"]));
        }
    }

    /// <summary>Smer zony/obchodu. Hodnoty kopiruju Pine `typ` (+1 = demand/long).</summary>
    public enum Direction
    {
        Long = 1,
        Short = -1
    }

    public enum SnapMode { Off, Floor, Ceil, Round }

    public enum OrderType { Limit, Market, Stop }

    /// <summary>Pomocne citanie enumov z retazcov, ako ich pisu JSON profily ("Long only", "Floor"...).</summary>
    public static class EnumText
    {
        public static SnapMode Snap(string s)
        {
            switch (s)
            {
                case "Off": return SnapMode.Off;
                case "Floor": return SnapMode.Floor;
                case "Ceil": return SnapMode.Ceil;
                case "Round": return SnapMode.Round;
            }
            throw new ArgumentException("neznamy snapMode '" + s + "'");
        }

        public static OrderType Order(string s)
        {
            switch (s)
            {
                case "Limit": return OrderType.Limit;
                case "Market": return OrderType.Market;
                case "Stop": return OrderType.Stop;
            }
            throw new ArgumentException("neznamy typ orderu '" + s + "'");
        }

        public static string Text(OrderType t)
        {
            return t == OrderType.Limit ? "Limit" : (t == OrderType.Market ? "Market" : "Stop");
        }
    }

    /// <summary>
    /// Velkost v cenovom priestore prenositelna medzi instrumentmi:
    /// `abs` cenove body, `ticks` x tick_size, `atr` nasobok ATR, `pct` percento z ceny.
    /// </summary>
    public sealed class SizeSpec
    {
        public readonly double Value;
        public readonly string Unit;

        public SizeSpec(double value, string unit)
        {
            if (unit != "abs" && unit != "ticks" && unit != "atr" && unit != "pct")
                throw new ArgumentException("neznama jednotka '" + unit + "', povolene: abs, atr, pct, ticks");
            if (value < 0) throw new ArgumentException("SizeSpec.value nesmie byt zaporna, dostal " + value);
            Value = value;
            Unit = unit;
        }

        /// <summary>Prepocita na vzdialenost v cene daneho instrumentu.</summary>
        public double Resolve(InstrumentSpec inst, double price, double atr)
        {
            if (Unit == "abs") return Value;
            if (Unit == "ticks") return Value * inst.TickSize;
            if (Unit == "atr") return Value * atr;
            return Value / 100.0 * price;
        }

        /// <summary>Hole cislo (-> defaultUnit) alebo {"value": ..., "unit": ...}.</summary>
        public static SizeSpec Parse(object raw, string defaultUnit)
        {
            Dictionary<string, object> d = raw as Dictionary<string, object>;
            if (d != null)
            {
                if (!d.ContainsKey("value")) throw new ArgumentException("SizeSpec dict musi mat kluc 'value'");
                return new SizeSpec(Json.ToDouble(d["value"]), Json.GetString(d, "unit", defaultUnit));
            }
            return new SizeSpec(Json.ToDouble(raw), defaultUnit);
        }
    }

    /// <summary>Vlastnosti instrumentu, ktore Pine berie zo `syminfo.*`.
    /// NinjaTrader: TickSize = Instrument.MasterInstrument.TickSize, PointValue = ...PointValue.</summary>
    public sealed class InstrumentSpec
    {
        public readonly string Symbol;
        public readonly string Venue;
        public readonly double TickSize;
        public readonly double PointValue;
        public readonly double QtyStep;
        public readonly double MinQty;
        public readonly bool HasRealVolume;

        public InstrumentSpec(string symbol, string venue, double tickSize, double pointValue,
                              double qtyStep, double minQty, bool hasRealVolume)
        {
            if (tickSize <= 0) throw new ArgumentException("InstrumentSpec.tick_size musi byt > 0");
            if (pointValue <= 0) throw new ArgumentException("InstrumentSpec.point_value musi byt > 0");
            if (qtyStep <= 0) throw new ArgumentException("InstrumentSpec.qty_step musi byt > 0");
            if (minQty <= 0) throw new ArgumentException("InstrumentSpec.min_qty musi byt > 0");
            Symbol = symbol; Venue = venue; TickSize = tickSize; PointValue = pointValue;
            QtyStep = qtyStep; MinQty = minQty; HasRealVolume = hasRealVolume;
        }

        public static InstrumentSpec FromJson(Dictionary<string, object> d)
        {
            return new InstrumentSpec(
                Json.GetString(d, "symbol", ""), Json.GetString(d, "venue", ""),
                Json.ToDouble(d["tick_size"]), Json.ToDouble(d["point_value"]),
                Json.GetDouble(d, "qty_step", 1.0), Json.GetDouble(d, "min_qty", 1.0),
                Json.GetBool(d, "has_real_volume", true));
        }

        public double TickDollarValue { get { return TickSize * PointValue; } }

        public double RoundPrice(double price) { return Math.Round(price / TickSize) * TickSize; }

        /// <summary>Zaokruhli nadol na `QtyStep` a podrz `MinQty`.</summary>
        public double RoundQty(double qty)
        {
            double stepped = Math.Floor(qty / QtyStep) * QtyStep;
            stepped = Math.Round(stepped, 12);
            return Math.Max(MinQty, stepped);
        }

        /// <summary>qty = risk / (SL vzdialenost v cene x hodnota bodu).</summary>
        public double QtyForRisk(double riskAmount, double slDistance)
        {
            if (riskAmount <= 0 || slDistance <= 0) return MinQty;
            return RoundQty(riskAmount / (slDistance * PointValue));
        }

        /// <summary>Doslovna replika Pine vypoctu vratane jeho chyby - pre golden testy.</summary>
        public double QtyForRiskPine(double riskAmount, double slDistance, double tickDollarValue)
        {
            if (riskAmount <= 0 || slDistance <= 0 || tickDollarValue <= 0) return 1.0;
            double perContract = (slDistance / TickSize) * tickDollarValue;
            if (perContract <= 0) return 1.0;
            return Math.Max(1.0, Math.Floor(riskAmount / perContract));
        }
    }
}
