// Citanie feather suborov (Arrow IPC file format, feather v2) bez NuGet - sviecky v `data/`
// a `data/archive/` pise pandas/pyarrow (Freqtrade, importery). Format:
//
//   "ARROW1" .. spravy (Schema, RecordBatch...) .. Footer (FlatBuffers) | int32 dlzka footera | "ARROW1"
//
// Footer nesie schemu a bloky record batchov; kazdy blok je sprava (metadata RecordBatch
// + telo s buffermi). Buffre su bud surove, alebo kazdy zvlast LZ4 frame s int64 nerozbalenou
// dlzkou na zaciatku (-1 = ulozeny bez kompresie). ZSTD tu nie je - nase subory ho nemaju
// a dekoder by bol vacsi nez cely zvysok.
//
// Podporovane stlpce: Int/UInt (8-64 bit), Float32/64, Bool, Timestamp, Date, Duration. Retazce
// a binarne stlpce sa preskocia (stlpec existuje, ale bez hodnot); vnorene typy a slovniky odmietne.
using System;
using System.Collections.Generic;
using System.IO;

namespace TradeBot.Backtest
{
    public enum FeatherKind { Int, Float, Bool, Timestamp, Date, Duration, Skipped }

    public sealed class FeatherColumn
    {
        public string Name;
        public FeatherKind Kind;
        /// <summary>Timestamp/Duration: 0 = s, 1 = ms, 2 = us, 3 = ns; Date: 0 = dni, 1 = ms.</summary>
        public int Unit;
        public string TimeZone;
        /// <summary>Hodnoty Float stlpca (null riadok = NaN).</summary>
        public double[] Doubles;
        /// <summary>Hodnoty ostatnych ciselnych stlpcov v povodnej jednotke (null riadok = 0).</summary>
        public long[] Longs;
        /// <summary>Platnost riadkov; null = vsetky platne.</summary>
        public bool[] Valid;

        internal int TypeId;
        internal int BitWidth;
        internal bool Signed;
    }

    public sealed class FeatherTable
    {
        public int Rows;
        public FeatherColumn[] Columns;

        public FeatherColumn Column(string name)
        {
            foreach (FeatherColumn c in Columns)
                if (c.Name == name) return c;
            throw new KeyNotFoundException("feather: chyba stlpec '" + name + "'");
        }

        /// <summary>Ciselny stlpec ako double[] (celociselne sa prevedu).</summary>
        public double[] Doubles(string name)
        {
            FeatherColumn c = Column(name);
            if (c.Doubles != null) return c.Doubles;
            if (c.Longs == null) throw new InvalidDataException("feather: stlpec '" + name + "' nie je ciselny");
            double[] d = new double[Rows];
            for (int i = 0; i < Rows; i++) d[i] = c.Valid != null && !c.Valid[i] ? double.NaN : c.Longs[i];
            return d;
        }

        /// <summary>Timestamp (alebo Date) stlpec v milisekundach od epochy.</summary>
        public long[] TimesMs(string name)
        {
            FeatherColumn c = Column(name);
            long mul = 1, div = 1;
            if (c.Kind == FeatherKind.Timestamp)
            {
                if (c.Unit == 0) mul = 1000;
                else if (c.Unit == 2) div = 1000;
                else if (c.Unit == 3) div = 1000000;
            }
            else if (c.Kind == FeatherKind.Date)
            {
                if (c.Unit == 0) mul = 86400000L;
            }
            else throw new InvalidDataException("feather: stlpec '" + name + "' nie je cas");
            long[] t = new long[Rows];
            for (int i = 0; i < Rows; i++)
            {
                long v = c.Longs[i];
                // delenie nadol (aj pred rokom 1970), ako pandas/numpy pri zmene jednotky
                t[i] = div == 1 ? v * mul : (v >= 0 ? v / div : -((-v + div - 1) / div));
            }
            return t;
        }
    }

    /// <summary>OHLCV sviecky so zaciatkom baru v ms UTC - tvar Freqtrade feather suboru.</summary>
    public sealed class Candles
    {
        public long[] Time;
        public double[] Open, High, Low, Close, Volume;
        public int Count { get { return Time.Length; } }
    }

    public static class Feather
    {
        private const int TypeNull = 1, TypeInt = 2, TypeFloat = 3, TypeBinary = 4, TypeUtf8 = 5, TypeBool = 6,
            TypeDate = 8, TypeTimestamp = 10, TypeDuration = 18, TypeLargeBinary = 19, TypeLargeUtf8 = 20;
        private const int HeaderRecordBatch = 3;

        private struct Seg
        {
            public byte[] B;
            public int Pos;
            public int Len;
        }

        public static FeatherTable Read(string path)
        {
            try
            {
                return Parse(File.ReadAllBytes(path));
            }
            catch (FormatException exc)
            {
                throw new InvalidDataException("feather " + path + ": " + exc.Message, exc);
            }
        }

        public static Candles ReadCandles(string path)
        {
            FeatherTable t = Read(path);
            Candles c = new Candles();
            c.Time = t.TimesMs("date");
            c.Open = t.Doubles("open");
            c.High = t.Doubles("high");
            c.Low = t.Doubles("low");
            c.Close = t.Doubles("close");
            c.Volume = t.Doubles("volume");
            return c;
        }

        public static FeatherTable Parse(byte[] b)
        {
            if (b.Length < 18 || !Magic(b, 0) || !Magic(b, b.Length - 6))
            {
                if (b.Length >= 4 && b[0] == 'F' && b[1] == 'E' && b[2] == 'A' && b[3] == '1')
                    throw new FormatException("feather v1 nie je podporovany (uloz cez pyarrow.feather.write_feather)");
                throw new FormatException("nie je to Arrow IPC subor (chyba ARROW1)");
            }
            int footerLen = BitConverter.ToInt32(b, b.Length - 10);
            FbTable footer = FbTable.Root(b, b.Length - 10 - footerLen);
            FbTable schema = footer.Table(1);
            if (schema.Int16(0, 0) != 0) throw new FormatException("big-endian subor nie je podporovany");

            int nf = schema.VectorLength(1);
            FeatherColumn[] cols = new FeatherColumn[nf];
            for (int i = 0; i < nf; i++) cols[i] = ParseField(schema.VectorTable(1, i));

            // bloky: struct { int64 offset; int32 metaDataLength; (4 B vypln); int64 bodyLength }
            int nb = footer.VectorLength(3);
            int blocks = nb == 0 ? 0 : footer.VectorStart(3);
            List<long> lengths = new List<long>();
            List<FbTable> batches = new List<FbTable>();
            List<int> bodies = new List<int>();
            long rows = 0;
            for (int i = 0; i < nb; i++)
            {
                int p = blocks + 24 * i;
                int off = checked((int)BitConverter.ToInt64(b, p));
                int metaLen = BitConverter.ToInt32(b, p + 8);
                int cont = BitConverter.ToInt32(b, off);
                int fb = cont == -1 ? off + 8 : off + 4; // starsi format nema 0xFFFFFFFF pred dlzkou
                FbTable msg = FbTable.Root(b, fb);
                if (msg.UInt8(1, 0) != HeaderRecordBatch) throw new FormatException("blok " + i + " nie je RecordBatch");
                FbTable rb = msg.Table(2);
                long n = rb.Int64(0, 0);
                batches.Add(rb);
                bodies.Add(off + metaLen);
                lengths.Add(n);
                rows += n;
            }
            if (rows > int.MaxValue) throw new FormatException("prilis vela riadkov");

            FeatherTable table = new FeatherTable();
            table.Rows = (int)rows;
            table.Columns = cols;
            foreach (FeatherColumn c in cols)
            {
                if (c.Kind == FeatherKind.Skipped) continue;
                if (c.Kind == FeatherKind.Float) c.Doubles = new double[rows];
                else c.Longs = new long[rows];
            }

            int at = 0;
            for (int k = 0; k < batches.Count; k++)
            {
                ReadBatch(b, batches[k], bodies[k], (int)lengths[k], cols, at);
                at += (int)lengths[k];
            }
            return table;
        }

        private static bool Magic(byte[] b, int p)
        {
            return b[p] == 'A' && b[p + 1] == 'R' && b[p + 2] == 'R' && b[p + 3] == 'O' && b[p + 4] == 'W' && b[p + 5] == '1';
        }

        private static FeatherColumn ParseField(FbTable f)
        {
            FeatherColumn c = new FeatherColumn();
            c.Name = f.String(0);
            c.TypeId = f.UInt8(2, 0);
            if (f.Has(4)) throw new FormatException("stlpec '" + c.Name + "': slovnikove kodovanie nie je podporovane");
            if (f.VectorLength(5) > 0) throw new FormatException("stlpec '" + c.Name + "': vnorene typy nie su podporovane");
            FbTable t = f.Has(3) ? f.Table(3) : default(FbTable);
            switch (c.TypeId)
            {
                case TypeInt:
                    c.Kind = FeatherKind.Int;
                    c.BitWidth = t.Int32(0, 0);
                    c.Signed = t.Bool(1, false);
                    break;
                case TypeFloat:
                    c.Kind = FeatherKind.Float;
                    int precision = t.Int16(0, 0);
                    if (precision == 0) throw new FormatException("stlpec '" + c.Name + "': float16 nie je podporovany");
                    c.BitWidth = precision == 1 ? 32 : 64;
                    break;
                case TypeBool:
                    c.Kind = FeatherKind.Bool;
                    break;
                case TypeTimestamp:
                    c.Kind = FeatherKind.Timestamp;
                    c.Unit = t.Int16(0, 0);
                    c.TimeZone = t.String(1);
                    c.BitWidth = 64;
                    c.Signed = true;
                    break;
                case TypeDate:
                    c.Kind = FeatherKind.Date;
                    c.Unit = t.Int16(0, 1);
                    c.BitWidth = c.Unit == 0 ? 32 : 64;
                    c.Signed = true;
                    break;
                case TypeDuration:
                    c.Kind = FeatherKind.Duration;
                    c.Unit = t.Int16(0, 1);
                    c.BitWidth = 64;
                    c.Signed = true;
                    break;
                case TypeNull:
                case TypeBinary:
                case TypeUtf8:
                case TypeLargeBinary:
                case TypeLargeUtf8:
                    c.Kind = FeatherKind.Skipped;
                    break;
                default:
                    throw new FormatException("stlpec '" + c.Name + "': typ Arrow " + c.TypeId + " nie je podporovany");
            }
            return c;
        }

        private static int BufferCount(int typeId)
        {
            if (typeId == TypeNull) return 0;
            if (typeId == TypeBinary || typeId == TypeUtf8 || typeId == TypeLargeBinary || typeId == TypeLargeUtf8) return 3;
            return 2;
        }

        private static void ReadBatch(byte[] b, FbTable rb, int body, int n, FeatherColumn[] cols, int at)
        {
            bool lz4 = false;
            if (rb.Has(3))
            {
                int codec = rb.Table(3).UInt8(0, 0);
                if (codec != 0) throw new FormatException("kompresia ZSTD nie je podporovana (uloz s compression='lz4')");
                lz4 = true;
            }
            // nodes: struct { int64 length; int64 null_count }, buffers: struct { int64 offset; int64 length }
            int nodes = rb.VectorStart(1);
            int bufs = rb.VectorLength(2) == 0 ? 0 : rb.VectorStart(2);
            int bi = 0;
            for (int ci = 0; ci < cols.Length; ci++)
            {
                FeatherColumn c = cols[ci];
                long nulls = BitConverter.ToInt64(b, nodes + 16 * ci + 8);
                int count = BufferCount(c.TypeId);
                if (c.Kind == FeatherKind.Skipped)
                {
                    bi += count;
                    continue;
                }
                Seg validity = Buffer(b, body, bufs, bi, lz4);
                Seg data = Buffer(b, body, bufs, bi + 1, lz4);
                bi += count;

                bool[] valid = null;
                if (nulls > 0 && validity.Len > 0)
                {
                    if (c.Valid == null)
                    {
                        c.Valid = new bool[c.Kind == FeatherKind.Float ? c.Doubles.Length : c.Longs.Length];
                        for (int i = 0; i < c.Valid.Length; i++) c.Valid[i] = true;
                    }
                    valid = c.Valid;
                    for (int i = 0; i < n; i++) valid[at + i] = Bit(validity, i);
                }
                Fill(c, data, n, at, valid);
            }
        }

        private static bool Bit(Seg s, int i)
        {
            return ((s.B[s.Pos + (i >> 3)] >> (i & 7)) & 1) != 0;
        }

        private static void Need(Seg s, int bytes, FeatherColumn c)
        {
            if (s.Len < bytes) throw new FormatException("stlpec '" + c.Name + "': buffer je kratsi, nez treba");
        }

        private static void Fill(FeatherColumn c, Seg s, int n, int at, bool[] valid)
        {
            if (c.Kind == FeatherKind.Float)
            {
                double[] d = c.Doubles;
                if (c.BitWidth == 64)
                {
                    Need(s, 8 * n, c);
                    System.Buffer.BlockCopy(s.B, s.Pos, d, 8 * at, 8 * n);
                }
                else
                {
                    Need(s, 4 * n, c);
                    for (int i = 0; i < n; i++) d[at + i] = BitConverter.ToSingle(s.B, s.Pos + 4 * i);
                }
                if (valid != null)
                    for (int i = 0; i < n; i++) if (!valid[at + i]) d[at + i] = double.NaN;
                return;
            }
            long[] l = c.Longs;
            if (c.Kind == FeatherKind.Bool)
            {
                Need(s, (n + 7) / 8, c);
                for (int i = 0; i < n; i++) l[at + i] = Bit(s, i) ? 1 : 0;
            }
            else if (c.BitWidth == 64)
            {
                Need(s, 8 * n, c);
                System.Buffer.BlockCopy(s.B, s.Pos, l, 8 * at, 8 * n);
            }
            else
            {
                int w = c.BitWidth / 8;
                Need(s, w * n, c);
                for (int i = 0; i < n; i++)
                {
                    int p = s.Pos + w * i;
                    long v;
                    if (w == 1) v = c.Signed ? (long)(sbyte)s.B[p] : s.B[p];
                    else if (w == 2) v = c.Signed ? (long)BitConverter.ToInt16(s.B, p) : BitConverter.ToUInt16(s.B, p);
                    else if (w == 4) v = c.Signed ? BitConverter.ToInt32(s.B, p) : (long)BitConverter.ToUInt32(s.B, p);
                    else throw new FormatException("stlpec '" + c.Name + "': sirka " + c.BitWidth + " bitov");
                    l[at + i] = v;
                }
            }
            if (valid != null)
                for (int i = 0; i < n; i++) if (!valid[at + i]) l[at + i] = 0;
        }

        private static Seg Buffer(byte[] b, int body, int bufs, int i, bool lz4)
        {
            Seg s = new Seg();
            int p = bufs + 16 * i;
            int off = body + checked((int)BitConverter.ToInt64(b, p));
            int len = checked((int)BitConverter.ToInt64(b, p + 8));
            if (len == 0 || !lz4)
            {
                s.B = b;
                s.Pos = off;
                s.Len = len;
                return s;
            }
            long raw = BitConverter.ToInt64(b, off);
            if (raw == -1)
            {
                s.B = b;
                s.Pos = off + 8;
                s.Len = len - 8;
                return s;
            }
            byte[] dst = new byte[checked((int)raw)];
            int got = Lz4.DecodeFrames(b, off + 8, off + len, dst, 0);
            if (got != dst.Length) throw new FormatException("LZ4 buffer dal " + got + " B namiesto " + dst.Length);
            s.B = dst;
            s.Pos = 0;
            s.Len = dst.Length;
            return s;
        }
    }
}
