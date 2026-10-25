// Citanie FlatBuffers bez kniznice - toto je len tolko, kolko treba na metadata Arrow IPC
// (Footer, Schema, Message, RecordBatch). Zapisovat netreba.
//
// Tabulka: na jej zaciatku je int32 posun k vtable (vtable = tabulka - posun); vtable ma uint16
// velkost seba, uint16 velkost tabulky a potom uint16 posun kazdeho pola (0 = pole chyba,
// plati default). Odkaz na tabulku / retazec / vektor je uint32 posun od miesta, kde lezi.
// Vsetko little-endian, rovnako ako BitConverter na x86 aj ARM.
using System;
using System.Text;

namespace TradeBot.Backtest
{
    internal struct FbTable
    {
        private readonly byte[] _b;
        private readonly int _pos;
        private readonly int _vt;
        private readonly int _vtLen;

        public FbTable(byte[] b, int pos)
        {
            _b = b;
            _pos = pos;
            _vt = pos - BitConverter.ToInt32(b, pos);
            _vtLen = BitConverter.ToUInt16(b, _vt);
        }

        /// <summary>Koren bufferu, ktory zacina na `start` (uint32 posun ku korenovej tabulke).</summary>
        public static FbTable Root(byte[] b, int start)
        {
            return new FbTable(b, start + BitConverter.ToInt32(b, start));
        }

        private int Field(int slot)
        {
            int o = 4 + 2 * slot;
            if (o >= _vtLen) return 0;
            int off = BitConverter.ToUInt16(_b, _vt + o);
            return off == 0 ? 0 : _pos + off;
        }

        private int Deref(int p)
        {
            return p + BitConverter.ToInt32(_b, p);
        }

        public bool Has(int slot) { return Field(slot) != 0; }

        public long Int64(int slot, long def) { int p = Field(slot); return p == 0 ? def : BitConverter.ToInt64(_b, p); }
        public int Int32(int slot, int def) { int p = Field(slot); return p == 0 ? def : BitConverter.ToInt32(_b, p); }
        public int Int16(int slot, int def) { int p = Field(slot); return p == 0 ? def : BitConverter.ToInt16(_b, p); }
        public int UInt8(int slot, int def) { int p = Field(slot); return p == 0 ? def : _b[p]; }
        public bool Bool(int slot, bool def) { int p = Field(slot); return p == 0 ? def : _b[p] != 0; }

        public FbTable Table(int slot)
        {
            int p = Field(slot);
            if (p == 0) throw new FormatException("FlatBuffers: chyba povinna tabulka v poli " + slot);
            return new FbTable(_b, Deref(p));
        }

        public string String(int slot)
        {
            int p = Field(slot);
            if (p == 0) return null;
            int s = Deref(p);
            return Encoding.UTF8.GetString(_b, s + 4, BitConverter.ToInt32(_b, s));
        }

        public int VectorLength(int slot)
        {
            int p = Field(slot);
            return p == 0 ? 0 : BitConverter.ToInt32(_b, Deref(p));
        }

        /// <summary>Pozicia prveho prvku vektora v bufferi (pre vektory structov).</summary>
        public int VectorStart(int slot)
        {
            int p = Field(slot);
            if (p == 0) throw new FormatException("FlatBuffers: chyba vektor v poli " + slot);
            return Deref(p) + 4;
        }

        public FbTable VectorTable(int slot, int i)
        {
            int e = VectorStart(slot) + 4 * i;
            return new FbTable(_b, Deref(e));
        }
    }
}
