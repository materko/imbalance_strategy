// Platformovo neutralne prikazy na kreslenie + paleta - zrkadlo `tradebot/core/drawing.py`.
// Engine NIKDY nekresli sam - vracia zoznam `DrawCommand`; adapter ich premeni na nativne objekty.
// Druh kresby (`Kind`) je otvoreny retazec: jadro pozna len genericke druhy, strategia si prida svoje.
using System;
using System.Collections.Generic;
using System.Globalization;

namespace TradeBot.Core
{
    /// <summary>Farby ako hex - Pine sekcia „DESIGN SYSTEM". LONG je zamerne cervena, SHORT modra.</summary>
    public static class Palette
    {
        public const string Long = "#be3c46";
        public const string Short = "#3b82f6";
        public const string Strong = "#10b981";
        public const string Amber = "#d97706";
        public const string Slate = "#334155";
        public const string Gray = "#94a3b8";
        public const string Session1 = "#6366f1";
        public const string Session2 = "#0d9488";
        public const string Session3 = "#9333ea";

        /// <summary>Pine `color.new(c, transparency)` -> hex s alfa kanalom (0 = nepriehladne).</summary>
        public static string WithAlpha(string color, int transparency)
        {
            if (transparency < 0 || transparency > 100)
                throw new ArgumentException("transparency musi byt 0-100, je " + transparency);
            int alpha = (int)Math.Round((100 - transparency) / 100.0 * 255);
            return color + alpha.ToString("x2", CultureInfo.InvariantCulture);
        }

        /// <summary>Pine `f_zoneColor`.</summary>
        public static string ZoneColor(int direction, bool strong)
        {
            if (strong) return Strong;
            return direction == 1 ? Long : Short;
        }
    }

    /// <summary>Genericke druhy kresieb (obchod a seansa); strategie pridavaju vlastne retazce.</summary>
    public static class DrawKinds
    {
        public const string TpBox = "tp_box";
        public const string SlBox = "sl_box";
        public const string Entry = "entry";
        public const string Exit = "exit";
        public const string Session = "session";
    }

    public static class LineStyles
    {
        public const string Solid = "solid";
        public const string Dotted = "dotted";
        public const string Dashed = "dashed";
    }

    public static class LabelStyles
    {
        public const string None = "none";
        public const string Up = "up";
        public const string Down = "down";
        public const string Left = "left";
    }

    public abstract class DrawCommand
    {
        public string ObjId = "";

        /// <summary>Zapise prikaz ako JSON objekt (protokol mosta do Pythonu, export grafu).</summary>
        public abstract void WriteJson(JsonWriter w);
    }

    /// <summary>Obdlznik. Suradnice X su cas v ms, nie index baru.</summary>
    public sealed class DrawBox : DrawCommand
    {
        public string Kind;
        public long X1Ms;
        public double Y1;
        public long X2Ms;
        public double Y2;
        public string BorderColor;
        public string FillColor;
        public string BorderStyle = LineStyles.Solid;
        public int BorderWidth = 1;
        public bool ExtendRight;
        public int? ZoneUid;
        public string Text = "";

        public DrawBox(string kind, long x1Ms, double y1, long x2Ms, double y2, string borderColor)
        {
            if (x2Ms < x1Ms) throw new ArgumentException("box konci pred zaciatkom: " + x1Ms + " -> " + x2Ms);
            Kind = kind; X1Ms = x1Ms; Y1 = y1; X2Ms = x2Ms; Y2 = y2; BorderColor = borderColor;
        }

        public override void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("t").Value("box").Key("k").Value(Kind).Key("id").Value(ObjId);
            w.Key("x1").Value(X1Ms).Key("y1").Value(Y1).Key("x2").Value(X2Ms).Key("y2").Value(Y2);
            w.Key("bc").Value(BorderColor);
            if (FillColor != null) w.Key("fc").Value(FillColor);
            if (BorderStyle != LineStyles.Solid) w.Key("bs").Value(BorderStyle);
            if (BorderWidth != 1) w.Key("bw").Value(BorderWidth);
            if (ExtendRight) w.Key("er").Value(true);
            if (ZoneUid.HasValue) w.Key("z").Value(ZoneUid.Value);
            if (!string.IsNullOrEmpty(Text)) w.Key("tx").Value(Text);
            w.EndObject();
        }
    }

    public sealed class DrawLine : DrawCommand
    {
        public string Kind;
        public long X1Ms;
        public double Y1;
        public long X2Ms;
        public double Y2;
        public string Color;
        public string Style = LineStyles.Solid;
        public int Width = 1;
        public int? ZoneUid;
        public string Text = "";

        public DrawLine(string kind, long x1Ms, double y1, long x2Ms, double y2, string color)
        {
            Kind = kind; X1Ms = x1Ms; Y1 = y1; X2Ms = x2Ms; Y2 = y2; Color = color;
        }

        public override void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("t").Value("line").Key("k").Value(Kind).Key("id").Value(ObjId);
            w.Key("x1").Value(X1Ms).Key("y1").Value(Y1).Key("x2").Value(X2Ms).Key("y2").Value(Y2);
            w.Key("c").Value(Color);
            if (Style != LineStyles.Solid) w.Key("s").Value(Style);
            if (Width != 1) w.Key("w").Value(Width);
            if (ZoneUid.HasValue) w.Key("z").Value(ZoneUid.Value);
            if (!string.IsNullOrEmpty(Text)) w.Key("tx").Value(Text);
            w.EndObject();
        }
    }

    public sealed class DrawLabel : DrawCommand
    {
        public string Kind;
        public long XMs;
        public double Y;
        public string Text;
        public string Color;
        public string Style = LabelStyles.None;
        public bool Above = true;
        public string BgColor;
        public int? ZoneUid;

        public DrawLabel(string kind, long xMs, double y, string text, string color)
        {
            Kind = kind; XMs = xMs; Y = y; Text = text; Color = color;
        }

        public override void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("t").Value("label").Key("k").Value(Kind).Key("id").Value(ObjId);
            w.Key("x").Value(XMs).Key("y").Value(Y).Key("tx").Value(Text).Key("c").Value(Color);
            w.Key("ab").Value(Above);
            if (Style != LabelStyles.None) w.Key("s").Value(Style);
            if (BgColor != null) w.Key("bg").Value(BgColor);
            if (ZoneUid.HasValue) w.Key("z").Value(ZoneUid.Value);
            w.EndObject();
        }
    }

    /// <summary>Pine `bgcolor()` - zvisly pas cez celu vysku grafu.</summary>
    public sealed class DrawBg : DrawCommand
    {
        public string Kind;
        public long X1Ms;
        public long X2Ms;
        public string Color;
        public string Text = "";

        public DrawBg(string kind, long x1Ms, long x2Ms, string color)
        {
            Kind = kind; X1Ms = x1Ms; X2Ms = x2Ms; Color = color;
        }

        public override void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("t").Value("bg").Key("k").Value(Kind).Key("id").Value(ObjId);
            w.Key("x1").Value(X1Ms).Key("x2").Value(X2Ms).Key("c").Value(Color);
            if (!string.IsNullOrEmpty(Text)) w.Key("tx").Value(Text);
            w.EndObject();
        }
    }

    /// <summary>Pine `box.set_*` / `label.set_*` - zmena uz nakresleneho objektu.
    /// `Field` je nazov atributu v Python tvare (`x2_ms`, `fill_color`...), aby sa protokol nelisil.</summary>
    public sealed class DrawUpdate : DrawCommand
    {
        public string Field;
        public object Value;

        public DrawUpdate(string objId, string field, object value)
        {
            ObjId = objId; Field = field; Value = value;
        }

        public override void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("t").Value("update").Key("id").Value(ObjId).Key("f").Value(Field);
            w.Key("v").ValueObject(Value);
            w.EndObject();
        }
    }

    /// <summary>Pine `box.delete` / `label.delete`.</summary>
    public sealed class DrawDelete : DrawCommand
    {
        public DrawDelete(string objId) { ObjId = objId; }

        public override void WriteJson(JsonWriter w)
        {
            w.BeginObject();
            w.Key("t").Value("delete").Key("id").Value(ObjId);
            w.EndObject();
        }
    }

    /// <summary>Prehra prikazy a drzi finalny stav objektov - to, co je na grafe vidiet.
    /// Adapter, ktory kresli nativne (NinjaTrader), si podla neho najde objekt, ktory ma zmenit.</summary>
    public sealed class DrawRegistry
    {
        private readonly Dictionary<string, DrawCommand> _objects = new Dictionary<string, DrawCommand>();

        public DrawCommand Find(string objId)
        {
            DrawCommand o;
            return _objects.TryGetValue(objId, out o) ? o : null;
        }

        public int Count { get { return _objects.Count; } }

        /// <summary>Vrati objekt, ktoreho sa prikaz tyka (novy, zmeneny alebo zmazany), alebo null.</summary>
        public DrawCommand Apply(DrawCommand cmd)
        {
            DrawUpdate up = cmd as DrawUpdate;
            if (up != null)
            {
                DrawCommand target = Find(up.ObjId);
                if (target != null) SetField(target, up.Field, up.Value);
                return target;
            }
            if (cmd is DrawDelete)
            {
                DrawCommand gone = Find(cmd.ObjId);
                _objects.Remove(cmd.ObjId);
                return gone;
            }
            if (string.IsNullOrEmpty(cmd.ObjId)) throw new ArgumentException("objekt bez obj_id sa neda updatovat");
            _objects[cmd.ObjId] = cmd;
            return cmd;
        }

        private static void SetField(DrawCommand o, string field, object value)
        {
            DrawBox box = o as DrawBox;
            DrawLine line = o as DrawLine;
            DrawLabel label = o as DrawLabel;
            DrawBg bg = o as DrawBg;
            switch (field)
            {
                case "x2_ms":
                    if (box != null) box.X2Ms = Convert.ToInt64(value);
                    else if (line != null) line.X2Ms = Convert.ToInt64(value);
                    else if (bg != null) bg.X2Ms = Convert.ToInt64(value);
                    break;
                case "x1_ms":
                    if (box != null) box.X1Ms = Convert.ToInt64(value);
                    else if (line != null) line.X1Ms = Convert.ToInt64(value);
                    else if (bg != null) bg.X1Ms = Convert.ToInt64(value);
                    break;
                case "y1": if (box != null) box.Y1 = Convert.ToDouble(value); else if (line != null) line.Y1 = Convert.ToDouble(value); break;
                case "y2": if (box != null) box.Y2 = Convert.ToDouble(value); else if (line != null) line.Y2 = Convert.ToDouble(value); break;
                case "border_color": if (box != null) box.BorderColor = (string)value; break;
                case "fill_color": if (box != null) box.FillColor = (string)value; break;
                case "color":
                    if (line != null) line.Color = (string)value;
                    else if (label != null) label.Color = (string)value;
                    else if (bg != null) bg.Color = (string)value;
                    break;
                case "text":
                    if (label != null) label.Text = (string)value;
                    else if (box != null) box.Text = (string)value;
                    else if (line != null) line.Text = (string)value;
                    break;
                case "x_ms": if (label != null) label.XMs = Convert.ToInt64(value); break;
                case "y": if (label != null) label.Y = Convert.ToDouble(value); break;
            }
        }
    }
}
