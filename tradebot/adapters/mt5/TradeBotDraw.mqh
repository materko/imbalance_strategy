//+------------------------------------------------------------------+
//| TradeBotDraw.mqh - DrawCommand engine-u -> objekty grafu MetaTrader 5                              |
//|                                                                                                   |
//| Zrkadlo `Render`/`Paint` z NinjaTrader adaptera. Format prikazov je v                              |
//| `csharp/TradeBot.Core/Drawing.cs` (`DrawCommand.WriteJson`):                                       |
//|   box    {t:"box",k,id,x1,y1,x2,y2,bc,fc?,bs?,bw?,er?,z?,tx?}                                       |
//|   line   {t:"line",k,id,x1,y1,x2,y2,c,s?,w?,z?,tx?}                                                 |
//|   label  {t:"label",k,id,x,y,tx,c,ab,s?,bg?,z?}                                                     |
//|   bg     {t:"bg",k,id,x1,x2,c,tx?}          (Pine bgcolor - zvisly pas)                             |
//|   update {t:"update",id,f,v}                (x1_ms,x2_ms,y1,y2,border_color,fill_color,color,text,x_ms,y)|
//|   delete {t:"delete",id}                                                                            |
//|                                                                                                   |
//| Registrom objektov je sam graf: update/delete najdu objekt podla mena `TB_<id>`. MT5 nema           |
//| priehladnost objektov, preto sa alfa z "#rrggbbaa" zmiesa s farbou pozadia grafu a vyplnene        |
//| objekty idu do pozadia (OBJPROP_BACK), aby neprekryli sviecky. Box s vyplnou aj okrajom su dva      |
//| objekty (`TB_<id>` vypln, `TB_<id>_b` okraj), lebo vyplneny obdlznik v MT5 okraj nekresli.          |
//+------------------------------------------------------------------+
#property strict

#include <TradeBot/TradeBotJson.mqh>

#define TB_OBJ_PREFIX "TB_"
#define TB_BG_TOP     1.0e9   // "cela vyska grafu" pre bgcolor pas

string TbObjName(string id) { return TB_OBJ_PREFIX + id; }

/// Dva hex znaky -> 0..255 (StringToInteger hex nepozna).
int TbHex(string s, int pos)
  {
   int v = 0;
   for(int i = pos; i < pos + 2 && i < StringLen(s); i++)
     {
      ushort c = StringGetCharacter(s, i);
      int d = c >= '0' && c <= '9' ? c - '0' : (c >= 'a' && c <= 'f' ? c - 'a' + 10 : (c >= 'A' && c <= 'F' ? c - 'A' + 10 : 0));
      v = v * 16 + d;
     }
   return v;
  }

/// "#rrggbb" / "#rrggbbaa" -> farba MT5 zmiesana s pozadim podla alfy; `visible` = false pri alfe 0 alebo prazdnom retazci.
color TbColor(string hex, bool &visible)
  {
   visible = false;
   if(StringLen(hex) < 7 || StringGetCharacter(hex, 0) != '#') return clrNONE;
   int r = TbHex(hex, 1), g = TbHex(hex, 3), b = TbHex(hex, 5);
   double a = StringLen(hex) >= 9 ? TbHex(hex, 7) / 255.0 : 1.0;
   if(a <= 0.0) return clrNONE;
   visible = true;
   color bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   int br = bg & 0xFF, bgg = (bg >> 8) & 0xFF, bb = (bg >> 16) & 0xFF;
   r = (int)MathRound(br + (r - br) * a);
   g = (int)MathRound(bgg + (g - bgg) * a);
   b = (int)MathRound(bb + (b - bb) * a);
   return (color)(r | (g << 8) | (b << 16));
  }

ENUM_LINE_STYLE TbLineStyle(string s)
  {
   if(s == "dotted") return STYLE_DOT;
   if(s == "dashed") return STYLE_DASH;
   return STYLE_SOLID;
  }

void TbCommonProps(string name, bool back)
  {
   ObjectSetInteger(0, name, OBJPROP_BACK, back);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, name, OBJPROP_SELECTED, false);
   ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);   // nie v zozname objektov - su ich tisice
  }

/// Obdlznik (novy alebo prekresleny): `fill` = vyplneny do pozadia, inak len okraj.
void TbRect(string name, datetime t1, double p1, datetime t2, double p2, color c, bool fill, int width, ENUM_LINE_STYLE style, string text)
  {
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   else { ObjectMove(0, name, 0, t1, p1); ObjectMove(0, name, 1, t2, p2); }
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FILL, fill);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   if(text != "") ObjectSetString(0, name, OBJPROP_TEXT, text);
   TbCommonProps(name, true);
  }

void TbBox(CJson *o, datetime t1, datetime t2)
  {
   string name = TbObjName(o.Str("id"));
   double y1 = o.Dbl("y1"), y2 = o.Dbl("y2");
   bool fillVisible, borderVisible;
   color fill = TbColor(o.Str("fc"), fillVisible);
   color border = TbColor(o.Str("bc"), borderVisible);
   int bw = o.Find("bw") != NULL ? (int)o.Dbl("bw") : 1;
   if(bw <= 0) borderVisible = false;
   ENUM_LINE_STYLE bs = TbLineStyle(o.Str("bs"));
   string text = o.Str("tx");
   if(fillVisible)
     {
      TbRect(name, t1, y1, t2, y2, fill, true, 1, STYLE_SOLID, text);
      if(borderVisible) TbRect(name + "_b", t1, y1, t2, y2, border, false, bw, bs, text);
      else ObjectDelete(0, name + "_b");
     }
   else
     {
      ObjectDelete(0, name + "_b");
      if(borderVisible) TbRect(name, t1, y1, t2, y2, border, false, bw, bs, text);
      else ObjectDelete(0, name);
     }
  }

void TbLine(CJson *o, datetime t1, datetime t2)
  {
   string name = TbObjName(o.Str("id"));
   bool visible;
   color c = TbColor(o.Str("c"), visible);
   if(!visible) { ObjectDelete(0, name); return; }
   double y1 = o.Dbl("y1"), y2 = o.Dbl("y2");
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_TREND, 0, t1, y1, t2, y2);
   else { ObjectMove(0, name, 0, t1, y1); ObjectMove(0, name, 1, t2, y2); }
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_STYLE, TbLineStyle(o.Str("s")));
   ObjectSetInteger(0, name, OBJPROP_WIDTH, o.Find("w") != NULL ? (int)o.Dbl("w") : 1);
   ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, o.Bool("er"));
   ObjectSetInteger(0, name, OBJPROP_RAY_LEFT, false);
   if(o.Str("tx") != "") ObjectSetString(0, name, OBJPROP_TEXT, o.Str("tx"));
   TbCommonProps(name, false);
  }

void TbLabel(CJson *o, datetime t)
  {
   string name = TbObjName(o.Str("id"));
   bool visible;
   color c = TbColor(o.Str("c"), visible);
   if(!visible) { ObjectDelete(0, name); return; }
   double y = o.Dbl("y");
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_TEXT, 0, t, y);
   else ObjectMove(0, name, 0, t, y);
   ObjectSetString(0, name, OBJPROP_TEXT, o.Str("tx"));
   ObjectSetString(0, name, OBJPROP_FONT, "Arial");
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   // `ab` = text nad bodom (kotva dole), inak pod nim (kotva hore); OBJ_TEXT pozadie nema, `bg` sa ignoruje
   bool above = o.Find("ab") == NULL || o.Bool("ab");
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, above ? ANCHOR_LOWER : ANCHOR_UPPER);
   TbCommonProps(name, false);
  }

void TbBg(CJson *o, datetime t1, datetime t2)
  {
   string name = TbObjName(o.Str("id"));
   bool visible;
   color c = TbColor(o.Str("c"), visible);
   if(!visible) { ObjectDelete(0, name); return; }
   TbRect(name, t1, 0.0, t2, TB_BG_TOP, c, true, 1, STYLE_SOLID, o.Str("tx"));
  }

/// Pine `box.set_*`/`label.set_*`: zmena atributu uz nakresleneho objektu (aj jeho okraja `_b`).
void TbUpdate(CJson *o)
  {
   string name = TbObjName(o.Str("id"));
   if(ObjectFind(0, name) < 0) return;
   string field = o.Str("f");
   CJson *v = o.Find("v");
   if(v == NULL) return;
   string border = name + "_b";
   bool hasBorder = ObjectFind(0, border) >= 0;
   bool visible;
   if(field == "x1_ms" || field == "x2_ms" || field == "x_ms")
     {
      int idx = field == "x2_ms" ? 1 : 0;
      datetime t = TbFromMs((long)v.num);
      ObjectMove(0, name, idx, t, ObjectGetDouble(0, name, OBJPROP_PRICE, idx));
      if(hasBorder) ObjectMove(0, border, idx, t, ObjectGetDouble(0, border, OBJPROP_PRICE, idx));
     }
   else if(field == "y1" || field == "y2" || field == "y")
     {
      int idx = field == "y2" ? 1 : 0;
      ObjectMove(0, name, idx, (datetime)ObjectGetInteger(0, name, OBJPROP_TIME, idx), v.num);
      if(hasBorder) ObjectMove(0, border, idx, (datetime)ObjectGetInteger(0, border, OBJPROP_TIME, idx), v.num);
     }
   else if(field == "border_color")
     {
      color c = TbColor(v.str, visible);
      if(hasBorder) { if(visible) ObjectSetInteger(0, border, OBJPROP_COLOR, c); else ObjectDelete(0, border); }
      else if(!ObjectGetInteger(0, name, OBJPROP_FILL)) { if(visible) ObjectSetInteger(0, name, OBJPROP_COLOR, c); else ObjectDelete(0, name); }
     }
   else if(field == "fill_color" || field == "color")
     {
      color c = TbColor(v.str, visible);
      if(visible) { ObjectSetInteger(0, name, OBJPROP_COLOR, c); if(field == "fill_color") ObjectSetInteger(0, name, OBJPROP_FILL, true); }
      else if(field == "fill_color" && hasBorder) ObjectDelete(0, name);   // ostane len okraj
      else ObjectDelete(0, name);
     }
   else if(field == "text")
      ObjectSetString(0, name, OBJPROP_TEXT, v.type == JSON_STRING ? v.str : DoubleToString(v.num, 2));
  }

/// Jeden prikaz engine-u. `TbFromMs` (ms UTC otvorenia baru -> cas servera) dava hostitel (TradeBotEA.mqh).
void TbDraw(CJson *o)
  {
   string t = o.Str("t");
   if(t == "box") TbBox(o, TbFromMs((long)o.Dbl("x1")), TbFromMs((long)o.Dbl("x2")));
   else if(t == "line") TbLine(o, TbFromMs((long)o.Dbl("x1")), TbFromMs((long)o.Dbl("x2")));
   else if(t == "label") TbLabel(o, TbFromMs((long)o.Dbl("x")));
   else if(t == "bg") TbBg(o, TbFromMs((long)o.Dbl("x1")), TbFromMs((long)o.Dbl("x2")));
   else if(t == "update") TbUpdate(o);
   else if(t == "delete") { string name = TbObjName(o.Str("id")); ObjectDelete(0, name); ObjectDelete(0, name + "_b"); }
  }

int TbObjectsCount() { return ObjectsTotal(0, -1, -1) > 0 ? ObjectsTotalPrefix() : 0; }

int ObjectsTotalPrefix()
  {
   int n = 0, total = ObjectsTotal(0, -1, -1);
   for(int i = 0; i < total; i++)
      if(StringFind(ObjectName(0, i, -1, -1), TB_OBJ_PREFIX) == 0) n++;
   return n;
  }
