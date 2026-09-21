# Big 7 do IBS stratégie — čo presne vložiť a kam

Blok kódu je v [big7_do_ibs.pine](big7_do_ibs.pine). Je písaný pre **Pine v6** (tvoja IBS
stratégia je v6, samostatný indikátor bol v5) a všetky mená má prefixované `b7`, takže sa
nemá ako pobiť s ničím, čo v stratégii už je.

Úpravy sú **štyri**: jedno vloženie bloku a tri jednoriadkové zmeny v STATE 4.

---

## 1. Vlož blok

Nájdi v skripte riadok:

```
// ==================== CONSTS ====================
```

a **tesne pred neho** vlož celý obsah `big7_do_ibs.pine`.

Prečo práve tam: v tom mieste sú už všetky `input.*()` hotové (Pine chce inputy pokope hore)
a blok je pred prvým miestom, kde sa použije.

---

## 2. Pridaj `big7Ok` (STATE 4)

Nájdi riadok:

```pine
                    bool structureOk = not useStructureFilter or (typ == 1 and marketBias == 1) or (typ == -1 and marketBias == -1)
```

a **hneď pod neho** pridaj:

```pine
                    // Big 7 filter smeru: LONG zóna sa obchoduje len keď je kôš Nasdaqu na
                    // správnej strane, SHORT zrkadlovo. Vypnuté = f_b7Allows vracia vždy true.
                    bool big7Ok = f_b7Allows(typ)
```

---

## 3. Zaraď ho do `canTrade`

Nájdi riadok:

```pine
                    bool canTrade    = enableTrading and directionOk and not oppositeOpen and not oppositePending and structureOk and volumeEntryOk
```

a nahraď ho týmto (pribudlo len `and big7Ok` na konci):

```pine
                    bool canTrade    = enableTrading and directionOk and not oppositeOpen and not oppositePending and structureOk and volumeEntryOk and big7Ok
```

---

## 4. Dopln dôvod preskočenia

Aby ti na grafe pri preskočenej zóne písalo, že to zablokoval práve Big 7, a nie niečo iné.

Nájdi riadok začínajúci `string skipReason = not enableTrading ?` a nahraď ho:

```pine
                        string skipReason = not enableTrading ? "TRADING DISABLED" : (oppositeOpen ? "OPPOSITE POSITION" : (oppositePending ? "OPPOSITE ORDER PENDING" : (not structureOk ? "STRUCTURE MISMATCH" : (not volumeEntryOk ? "VOLUME INSUFFICIENT" : (not big7Ok ? "BIG7 DIRECTION MISMATCH" : "DIRECTION DISABLED")))))
```

Nájdi riadok začínajúci `string skipReasonDisp = not enableTrading ?` a nahraď ho:

```pine
                        string skipReasonDisp = not enableTrading ? f_tr("TRADING DISABLED", "OBCHODOVANIE VYPNUTÉ", "OBCHODOVÁNÍ VYPNUTO") : (oppositeOpen ? f_tr("OPPOSITE POSITION", "OPAČNÁ POZÍCIA", "OPAČNÁ POZICE") : (oppositePending ? f_tr("OPPOSITE ORDER PENDING", "OPAČNÝ ORDER ČAKÁ", "OPAČNÝ ORDER ČEKÁ") : (not structureOk ? f_tr("STRUCTURE MISMATCH", "ŠTRUKTÚRA NESEDÍ", "STRUKTURA NESEDÍ") : (not volumeEntryOk ? f_tr("VOLUME INSUFFICIENT", "NEDOSTATOČNÝ VOLUME", "NEDOSTATEČNÝ VOLUME") : (not big7Ok ? f_tr("BIG 7 DIRECTION MISMATCH", "BIG 7 NESEDÍ SO SMEROM", "BIG 7 NESEDÍ SE SMĚREM") : f_tr("DIRECTION DISABLED", "SMER VYPNUTÝ", "SMĚR VYPNUTÝ"))))))
```

V oboch pribudla jedna vetva a **jedna zátvorka navyše na konci** — keď to kopíruješ celé,
netreba nič dopočítavať.

---

## Ako sa to potom správa

| nastavenie | čo robí |
|---|---|
| **Big 7: filter smeru obchodov** | vypnuté (predvolené) = stratégia sa správa **presne ako doteraz**, filter nič neblokuje |
| **Pravidlo: Nula** | LONG zóna len keď skóre > 0, SHORT len keď < 0 (to, o čom sme sa bavili) |
| **Pravidlo: Prah** | skóre musí prekročiť ±Prah skóre — menej obchodov, silnejší kontext |
| **Pravidlo: Stav LONG/SELL** | musí byť potvrdený signál vrátane šírky a súhlasu SOXX — najprísnejšie |
| **Mimo burzových hodín: Prepustiť** | mimo 9:30–16:00 NY filter nerobí nič (predvolené) |
| **Mimo burzových hodín: Blokovať** | mimo burzových hodín sa neobchoduje vôbec |

Tvoj vlastný `Trade direction` ostáva **nadradený** — keď máš „Long only", Big 7 z toho
shorty nespraví, len môže longy zablokovať.

---

## Ako to zmerať

Toto je prvýkrát, čo sa Big 7 dá **odmerať** — ako samostatný indikátor sa nedal.

1. Strategy Tester, filter **vypnutý** → zapíš si počet obchodov, Profit Factor, Max Drawdown
2. Zapni filter, `Pravidlo = Nula` → to isté znova
3. Skús `Pravidlo = Prah` a `Stav LONG/SELL`

Porovnávaj na **tom istom období a tom istom nastavení IBS**. Zaujíma ťa, či filter zlepšil
Profit Factor viac, než o koľko ubral obchodov — ak z 300 obchodov spraví 120 a PF stúpne
z 1,3 na 1,4, je to slabší výsledok, nie lepší.

---

## Na čo si dať pozor

**Dáva to zmysel len na nástrojoch naviazaných na Nasdaq** — NAS100, MNQ, QQQ. Na zlate,
rope alebo krypte by Big 7 filter bol náhodný šum, ktorý len ubelí obchody.

**Skóre sa v stratégii nedá vykresliť do panelu.** IBS beží s `overlay=true` a Pine nevie
poslať plot do iného panelu. V stratégii dostaneš číslo, stav, tabuľku a filter — čiaru si
nechaj zobrazenú z indikátora vedľa, počíta to isté.

**Sleduj limit dotazov.** IBS má dnes 3 volania `request.security`, Big 7 pridá 18. Spolu 21
z povolených 40. Keby si pridával ďalšie multi-timeframe veci, toto je strop.

**`Trend: plné skóre pri sklone` závisí od timeframu grafu.** Na 15m nechaj 0,05; na 5m daj
okolo 0,025; na 1m okolo 0,005. Inak zložka trendu do skóre prakticky neprispeje.

**Big 7 filter nie je odmeraný na našich dátach.** V archíve nemáme jednotlivé akcie, takže
v našom Testeri sa to prehrať nedá — čísla ti dá len TradingView Strategy Tester.
