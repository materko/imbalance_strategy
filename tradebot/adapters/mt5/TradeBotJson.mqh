//+------------------------------------------------------------------+
//| TradeBotJson.mqh - minimalny JSON parser pre vystup engine-u                                       |
//|                                                                                                   |
//| MQL5 JSON natívne nečíta a engine vracia jeden JSON objekt na bar (`EngineHost.OnBar`). Parser je   |
//| zámerne maly: objekty, polia, retazce (s \" \\ \n \uXXXX), cisla, true/false/null. Strom sa uvolnuje |
//| cez `delete` korena (destruktor uvolni deti).                                                      |
//+------------------------------------------------------------------+
#property strict

enum ENUM_JSON_TYPE { JSON_NULL, JSON_BOOL, JSON_NUMBER, JSON_STRING, JSON_ARRAY, JSON_OBJECT };

class CJson
  {
public:
   ENUM_JSON_TYPE type;
   string         key;      // kluc v rodicovskom objekte ("" v poli)
   string         str;
   double         num;
   bool           flag;
   CJson         *items[];

                  CJson() : type(JSON_NULL), key(""), str(""), num(0), flag(false) {}
                 ~CJson() { for(int i = 0; i < ArraySize(items); i++) delete items[i]; }

   int            Size() const { return ArraySize(items); }
   CJson         *At(int i) { return items[i]; }
   CJson         *Find(string k)
     {
      for(int i = 0; i < ArraySize(items); i++) if(items[i].key == k) return items[i];
      return NULL;
     }
   string         Str(string k) { CJson *c = Find(k); return c == NULL ? "" : c.str; }
   double         Dbl(string k) { CJson *c = Find(k); return c == NULL ? 0 : c.num; }
   bool           Bool(string k) { CJson *c = Find(k); return c == NULL ? false : c.flag; }
   void           Add(CJson *c) { int n = ArraySize(items); ArrayResize(items, n + 1); items[n] = c; }
  };

class CJsonReader
  {
private:
   string m_text;
   int    m_pos;
   int    m_len;

   void   Ws() { while(m_pos < m_len) { ushort c = StringGetCharacter(m_text, m_pos); if(c == ' ' || c == '\t' || c == '\n' || c == '\r') m_pos++; else break; } }
   ushort Peek() { return m_pos < m_len ? StringGetCharacter(m_text, m_pos) : 0; }

   bool   ReadString(string &out)
     {
      if(Peek() != '"') return false;
      m_pos++;
      out = "";
      while(m_pos < m_len)
        {
         ushort c = StringGetCharacter(m_text, m_pos++);
         if(c == '"') return true;
         if(c != '\\') { out += ShortToString(c); continue; }
         if(m_pos >= m_len) return false;
         ushort e = StringGetCharacter(m_text, m_pos++);
         switch(e)
           {
            case 'n': out += "\n"; break;
            case 't': out += "\t"; break;
            case 'r': out += "\r"; break;
            case 'b': out += ShortToString(8); break;
            case 'f': out += ShortToString(12); break;
            case 'u':
              {
               if(m_pos + 4 > m_len) return false;
               int code = 0;
               for(int i = 0; i < 4; i++)
                 {
                  ushort h = StringGetCharacter(m_text, m_pos + i);
                  int v = h >= '0' && h <= '9' ? h - '0' : (h >= 'a' && h <= 'f' ? h - 'a' + 10 : (h >= 'A' && h <= 'F' ? h - 'A' + 10 : -1));
                  if(v < 0) return false;
                  code = code * 16 + v;
                 }
               m_pos += 4;
               out += ShortToString((ushort)code);
               break;
              }
            default: out += ShortToString(e); break;   // \" \\ \/
           }
        }
      return false;
     }

   bool   ReadNumber(double &out)
     {
      int start = m_pos;
      while(m_pos < m_len)
        {
         ushort c = StringGetCharacter(m_text, m_pos);
         if((c >= '0' && c <= '9') || c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E') m_pos++; else break;
        }
      if(m_pos == start) return false;
      out = StringToDouble(StringSubstr(m_text, start, m_pos - start));
      return true;
     }

   bool   Literal(string word)
     {
      if(StringSubstr(m_text, m_pos, StringLen(word)) != word) return false;
      m_pos += StringLen(word);
      return true;
     }

public:
   CJson *Parse(string text)
     {
      m_text = text; m_pos = 0; m_len = StringLen(text);
      CJson *root = Value();
      return root;
     }

   CJson *Value()
     {
      Ws();
      ushort c = Peek();
      CJson *node = new CJson();
      bool ok = false;
      if(c == '{')
        {
         node.type = JSON_OBJECT; m_pos++; Ws();
         ok = true;
         if(Peek() == '}') { m_pos++; return node; }
         while(m_pos < m_len)
           {
            Ws();
            string k;
            if(!ReadString(k)) { ok = false; break; }
            Ws();
            if(Peek() != ':') { ok = false; break; }
            m_pos++;
            CJson *child = Value();
            if(child == NULL) { ok = false; break; }
            child.key = k;
            node.Add(child);
            Ws();
            ushort d = Peek();
            if(d == ',') { m_pos++; continue; }
            if(d == '}') { m_pos++; break; }
            ok = false; break;
           }
        }
      else if(c == '[')
        {
         node.type = JSON_ARRAY; m_pos++; Ws();
         ok = true;
         if(Peek() == ']') { m_pos++; return node; }
         while(m_pos < m_len)
           {
            CJson *child = Value();
            if(child == NULL) { ok = false; break; }
            node.Add(child);
            Ws();
            ushort d = Peek();
            if(d == ',') { m_pos++; continue; }
            if(d == ']') { m_pos++; break; }
            ok = false; break;
           }
        }
      else if(c == '"') { node.type = JSON_STRING; ok = ReadString(node.str); }
      else if(c == 't') { node.type = JSON_BOOL; node.flag = true; ok = Literal("true"); }
      else if(c == 'f') { node.type = JSON_BOOL; node.flag = false; ok = Literal("false"); }
      else if(c == 'n') { node.type = JSON_NULL; ok = Literal("null"); }
      else { node.type = JSON_NUMBER; ok = ReadNumber(node.num); }
      if(!ok) { delete node; return NULL; }
      return node;
     }
  };

/// Strom z textu alebo NULL pri chybe; volajuci ho uvolni cez `delete`.
CJson *JsonParse(string text)
  {
   if(text == "") return NULL;
   CJsonReader reader;
   return reader.Parse(text);
  }
