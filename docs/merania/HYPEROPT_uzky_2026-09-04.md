# Druhý pokus o hyperopt — úzky priestor a iné skóre (2026-09-04)

Prvý hyperopt ([HYPEROPT_btcusdt_2026-09-04.md](HYPEROPT_btcusdt_2026-09-04.md))
ladil desať prahov a dopadol učebnicovo: víťaz mal na ladenom roku +34,8 %, ale
**všetky štyri** out-of-sample roky boli stratové. Tento beh je zopakovanie s troma
zmenami, ktoré mali presne túto chybu odstrániť.

## Čo bolo inak

**Tri parametre namiesto desiatich.** `rrRatio`, `slLookback` a `structureSwingLen` —
teda len tie, ktoré menia *štruktúru* obchodu, nie citlivosť filtra. Prahy v jednotke
`atr` aj prepínače entry modelov sú z priestoru von.

**Iné skóre — `IBSEdgeLoss`.** Maximalizuje **break-even poplatok**
(hrubý zisk ÷ obchodovaný objem), nie PnL. Pri poplatku 0,05 % je čistý PnL blízko
nuly a hyperopt by v ňom ladil hlavne šum; break-even poplatok je to isté číslo
očistené o veľkosť pozície aj o počet obchodov. Konfigurácia, ktorá zarobí rovnako
pri polovičnom objeme, je lepšia — a v tomto skóre to vidno okamžite.

**Dva roky bokom.** Ladilo sa na 2021-10 → 2024-10; 2024-10 → 2026-09 hyperopt
nikdy nevidel.

Východisko: profil `btcusdt_3m_binance_struct` (RR 5, `slLookback` 20, štruktúrny
filter, bez trailingu). 150 epoch, `--analyze-per-epoch`, ~50 minút.

## Výsledok

Najlepšia epocha (143/150):

| parameter | pred | po hyperopte |
|---|---|---|
| `rrRatio` | 5,0 | **7,7** |
| `slLookback` | 20 | **24** |
| `structureSwingLen` | 5 | **5** (nezmenené) |

Na ladenom okne skóre 0,1087 % — vyzeralo to ako veľký skok. Po rokoch je ale vidieť,
že to číslo ťahá jeden výnimočný rok:

| okno | | obchodov | hrubý PF | break-even |
|---|---|---|---|---|
| 2021-10 → 2022-10 | ladené | 86 | 2,801 | 0,1928 % |
| 2022-10 → 2023-10 | ladené | 107 | 1,319 | 0,0198 % |
| 2023-10 → 2024-10 | ladené | 106 | 1,584 | 0,0533 % |
| 2024-10 → 2025-10 | **odložené** | 94 | 1,502 | **0,0421 %** |
| 2025-09 → 2026-09 | **odložené** | 81 | 1,769 | **0,0567 %** |

## Priame porovnanie na odložených rokoch

| konfigurácia | 2024-10 → 2025-10 | 2025-09 → 2026-09 |
|---|---|---|
| RR 5 / lb 20 (ručne) | **0,0432 %** | **0,0568 %** |
| RR 7,7 / lb 24 (hyperopt) | 0,0421 % | 0,0567 % |

**Hyperopt nenašiel nič lepšie.** Na oboch odložených rokoch je jeho víťaz o chlp
horší než konfigurácia, ktorú sme mali predtým — rozdiel je hlboko v šume.

## Čo to napriek tomu povedalo

1. **Priestor je vyčerpaný.** Tri parametre, 150 epoch, a optimum sedí tam, kde sme
   ho našli ručne. `rrRatio` 7,7 proti 5 a `slLookback` 24 proti 20 sú v rámci šumu.
2. **`structureSwingLen` nemá rezervu.** Bol to jediný úplne neprebádaný parameter
   a hyperopt na ňom nenašiel nič lepšie než Pine default 5.
3. **Metodika tentokrát obstála.** Víťaz sa na odložených rokoch **nezrútil** —
   drží 0,042–0,057 %, teda to isté, čo na ladených. To je opak prvého hyperoptu.
   Nie je to zásluha šťastia: úzky priestor a skóre, ktoré nemeria PnL, robia presne
   toto.

Ďalší zisk teda z ladenia parametrov nepríde. Zostáva lacnejšia exekúcia — pri
edge okolo 0,05 % je rozdiel medzi taker (0,05 %) a maker (0,02 %) poplatkom
rozdielom medzi nulou a ziskom.

## Ako to zopakovať

```bash
TRADEBOT_PROFILE=btcusdt_3m_binance_struct \
./platforms/freqtrade/scripts/hyperopt.sh 20211001-20241001 150
```

`IBSEdgeLoss` je odteraz predvolená loss funkcia v oboch skriptoch.
