// Dekompresia LZ4 frame (https://github.com/lz4/lz4/blob/dev/doc/lz4_Frame_format.md) - pyarrow
// nim komprimuje kazdy buffer feather suboru (`compression="lz4"` je jeho default). Len citanie,
// bez kontroly kontrolnych suctov (xxHash): poskodeny subor sa prejavi nesediacou dlzkou.
using System;

namespace TradeBot.Backtest
{
    public static class Lz4
    {
        private const uint FrameMagic = 0x184D2204;
        private const uint SkippableMask = 0xFFFFFFF0;
        private const uint SkippableMagic = 0x184D2A50;

        /// <summary>Rozbali vsetky frame v src[pos, end) do dst od dstPos; vrati pocet zapisanych bajtov.</summary>
        public static int DecodeFrames(byte[] src, int pos, int end, byte[] dst, int dstPos)
        {
            int op = dstPos;
            while (pos < end)
            {
                uint magic = BitConverter.ToUInt32(src, pos);
                pos += 4;
                if ((magic & SkippableMask) == SkippableMagic)
                {
                    pos += 4 + BitConverter.ToInt32(src, pos);
                    continue;
                }
                if (magic != FrameMagic) throw new FormatException("LZ4: chyba magic frame na pozicii " + (pos - 4));
                int flg = src[pos];
                pos += 2; // FLG, BD
                if ((flg >> 6) != 1) throw new FormatException("LZ4: nepodporovana verzia frame");
                bool blockChecksum = (flg & 0x10) != 0;
                bool contentChecksum = (flg & 0x04) != 0;
                if ((flg & 0x08) != 0) pos += 8;
                if ((flg & 0x01) != 0) throw new FormatException("LZ4: frame so slovnikom nie je podporovany");
                pos += 1; // HC
                // zavisle bloky (bez B.Indep) siahaju do predoslych - tie su v tom istom dst hned pred nimi
                int frameStart = op;
                while (true)
                {
                    uint bs = BitConverter.ToUInt32(src, pos);
                    pos += 4;
                    if (bs == 0) break;
                    int size = (int)(bs & 0x7FFFFFFF);
                    if (pos + size > end) throw new FormatException("LZ4: blok za koncom dat");
                    if ((bs & 0x80000000) != 0)
                    {
                        if (op + size > dst.Length) throw new FormatException("LZ4: vystup je dlhsi, nez sa cakalo");
                        Buffer.BlockCopy(src, pos, dst, op, size);
                        op += size;
                    }
                    else
                    {
                        op = DecodeBlock(src, pos, pos + size, dst, op, frameStart);
                    }
                    pos += size;
                    if (blockChecksum) pos += 4;
                }
                if (contentChecksum) pos += 4;
            }
            return op - dstPos;
        }

        private static int DecodeBlock(byte[] s, int ip, int iend, byte[] d, int op, int dmin)
        {
            int dend = d.Length;
            while (true)
            {
                int token = s[ip++];
                int lit = token >> 4;
                if (lit == 15)
                {
                    int b;
                    do { b = s[ip++]; lit += b; } while (b == 255);
                }
                if (ip + lit > iend || op + lit > dend) throw new FormatException("LZ4: poskodeny blok (literaly)");
                Buffer.BlockCopy(s, ip, d, op, lit);
                ip += lit;
                op += lit;
                if (ip >= iend) break; // posledna sekvencia ma len literaly

                int off = s[ip] | (s[ip + 1] << 8);
                ip += 2;
                int ml = token & 15;
                if (ml == 15)
                {
                    int b;
                    do { b = s[ip++]; ml += b; } while (b == 255);
                }
                ml += 4;
                int m = op - off;
                if (off == 0 || m < dmin || op + ml > dend) throw new FormatException("LZ4: poskodeny blok (zhoda)");
                if (off >= ml)
                {
                    Buffer.BlockCopy(d, m, d, op, ml);
                    op += ml;
                }
                else
                {
                    // prekryv: zhoda opakuje prave zapisane bajty
                    for (int i = 0; i < ml; i++) d[op++] = d[m++];
                }
            }
            return op;
        }
    }
}
