# VWAP OP — ako funguje

> V jednej vete: presný prepis Pine skriptu „Drift VWAP Pullback“ — prvý dotyk VWAP v smere jeho sklonu na 15m, vstup market na 5m grafe.

## Ako vznikne obchod
1. **VWAP** od 9:30 New York z 15m sviečok (vždy posledná uzavretá 15m perióda — bez prekresľovania).
2. **Drift** = zmena VWAP za posledné 15m periódy porovnaná s ATR 15m. Nad prahom = smer long, pod = short, inak sa neobchoduje (počíta sa nanovo na každej sviečke).
3. **Odchod:** cena musí byť najprv celá mimo pásma okolo VWAP.
4. **Pullback:** sviečka sa dotkne VWAP (v tolerancii) a zavrie späť na strane driftu → market vstup na jej zavretí.

## Stop a cieľ
- Stop pevne za VWAP, cieľ = stop × RR, voliteľný posun stopu na vstup po +1R.
- Voliteľne len prvý pullback dňa v danom smere.

## Rozdiel oproti VWAP Session
VWAP Session je voľná rekonštrukcia rovnakej myšlienky s mnohými nastaveniami; VWAP OP je doslovný port jedného konkrétneho skriptu.

## Slovníček
- **VWAP** — priemerná cena dňa vážená objemom (od otvorenia); ukazuje „férovú“ cenu dňa podľa obchodovaného objemu.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe.
- **RR (risk:reward)** — pomer cieľa k stopu. RR 2 = cieľ je dvakrát ďalej ako stop.
