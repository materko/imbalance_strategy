# Filtre vstupu: štruktúrny a volume (2026-09-04)

Predchádzajúce meranie ukázalo, že celá strata vzniká v prvých 30 minútach po vstupe
a širším stopom sa neodstráni ([HYPOTEZA_koniec_seansy_2026-09-04.md](HYPOTEZA_koniec_seansy_2026-09-04.md)).
Zostávala teda možnosť, že chyba je vo **vstupe**.

Pine má dva vstupné filtre, ktoré boli celý čas **vypnuté** a nikdy sme ich netestovali:

* `useStructureFilter` — „Obchoduj len v smere štruktúry (BOS/CHoCH)". LONG sa umiestni
  len keď je posledný break smerom hore.
* `useVolumeFilter` + `volumeFilterBlockTrading` — zóna s nedostatočným volume sa
  vôbec nevytvorí.

Základ: RR 5, `slLookback` 20, bez trailingu, Long only, všetky tri entry modely,
S/R aj likvidita. Merané na **piatich rokoch naraz**, bez poplatkov (aby bol vidieť
samotný edge), a kľúčové číslo je break-even poplatok.

## Výsledok

Break-even poplatok (% na stranu), po rokoch:

| variant | 2021-22 | 2022-23 | 2023-24 | 2024-25 | 2025-26 | **priemer** | obchodov/rok |
|---|---|---|---|---|---|---|---|
| bez filtrov | 0,0444 | 0,0043 | 0,0154 | 0,0219 | 0,0270 | **0,0226 %** | 203 |
| **štruktúra** | **0,1398** | −0,0032 | 0,0156 | **0,0397** | **0,0568** | **0,0497 %** | **96** |
| volume | 0,0907 | 0,0054 | −0,0489 | 0,0529 | 0,0034 | 0,0207 % | 59 |
| oba | 0,3828 | 0,0053 | −0,1058 | 0,1094 | 0,3219 | 0,1427 % | 14 |

**Štruktúrny filter zdvojnásobí edge** (0,0226 → 0,0497 %) a zároveň zníži počet
obchodov na polovicu. Priemerný break-even poplatok 0,0497 % sa už prakticky rovná
tomu, čo berie Binance (0,05 %).

**Volume filter nepomáha** — priemer sa nezmení a rozptyl po rokoch je väčší
(v jednom roku −0,0489 %).

**Kombinácia oboch vyzerá najlepšie, ale je to ilúzia**: 14 obchodov za rok je
príliš málo na akýkoľvek záver a hodnoty po rokoch skáču od −0,1058 do +0,3828.

## Prečo štruktúrny filter funguje

Posledný rok, ten istý beh s filtrom a bez neho:

| | bez filtra | so štruktúrou |
|---|---|---|
| TP | 28 (+19 792) | 17 (+10 833) |
| koniec seansy | 21 (+13 334), 90,5 % W | 10 (+7 803), **100 % W** |
| SL | **125** (−24 946) | **55** (−10 353) |
| spolu | 174 obchodov, +8 180 | **82 obchodov, +8 283** |

Filter necháva **rovnaký hrubý zisk pri polovičnom počte obchodov**. Odrezáva
neúmerne veľa stratových: SL padne zo 125 na 55, kým TP len z 28 na 17. To je presne
ten typ zlepšenia, na ktorý sme čakali — nezvyšuje zisk, ale prestáva platiť za
obchody, ktoré aj tak nič nezarobili.

## S reálnymi poplatkami

RR 5, `slLookback` 20, štruktúrny filter, poplatok 0,05 %/strana, peňaženka 10 000 USDT:

| okno | obchodov | WR | hrubý PF | **čistý PnL** | max DD |
|---|---|---|---|---|---|
| 2021-10 → 2022-10 | 87 | 26,4 % | 2,076 | **+13,97 %** | 7,65 % |
| 2022-10 → 2023-10 | 107 | 26,2 % | 1,368 | −4,82 % | 9,87 % |
| 2023-10 → 2024-10 | 106 | 21,7 % | 1,315 | −4,39 % | 10,73 % |
| 2024-09 → 2025-09 | 96 | 24,0 % | 1,414 | −2,49 % | 5,22 % |
| 2025-09 → 2026-09 | 82 | 32,9 % | 1,675 | **+0,58 %** | 5,78 % |

**Dva z piatich rokov sú po poplatkoch ziskové** a súčet za päť rokov je +285 USDT,
teda prakticky nula. Drawdowny klesli z 11–13 % na 5–11 %.

Hrubý profit factor cez všetkých 478 obchodov je **1,588** (bez filtra 1,29).

## Kde to sme

| krok | priemerný break-even poplatok |
|---|---|
| pôvodné nastavenie (RR 1, trailing) | 0,0050 % |
| RR 5, bez trailingu | 0,0159 % |
| + `slLookback` 20 | 0,0226 % |
| **+ štruktúrny filter** | **0,0497 %** |
| *Binance berie* | *0,0500 %* |

Za celú sériu meraní sa edge zdesaťnásobil a **dorovnal poplatky**. To znamená
nula, nie zisk: stratégia je teraz zhruba na hranici, kde poplatky zjedia presne
to, čo zarobí.

## Profil

Uložené ako `ibs/configs/btcusdt_3m_binance_struct.json`:

```bash
IBS_PROFILE=btcusdt_3m_binance_struct ./platforms/freqtrade/scripts/backtest.sh
```

**Nie je to odporúčanie na obchodovanie** — je to najlepšia konfigurácia, akú sa
podarilo nájsť, a jej výsledok je po poplatkoch nula.

## Čo ďalej

1. **Lacnejšia exekúcia je teraz rovnako veľká páka ako stratégia.** Maker vstup
   (0,02 %) namiesto taker by pri tomto edge znamenal rozdiel medzi nulou a ziskom.
   Vstupy sú aj tak limitky, takže to nie je nereálne — treba overiť, koľko z nich
   by sa reálne vyplnilo ako maker.
2. Filtre sa doteraz testovali len zapnuté/vypnuté. `structureSwingLen` (5) sa
   nikdy neladil.
3. Volume filter zahodiť.
