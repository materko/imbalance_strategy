# MTK ZONE — ako funguje

> V jednej vete: kreslí SD zóny na vyššom TF (5m / 15m) len tam, kde sa zhodnú aspoň dve veci — vzor zóny, vrchol volume profilu a prudký nárast objemu — a vstupuje do nich na grafe 3m / 2m limitom, modelom IBS alebo pin barom.

## Ako vznikne zóna
Bary grafu sa skladajú na TF zón (predvolene 5m, voliteľne aj 15m). Na každej uzavretej sviečke toho TF stratégia hľadá tri veci:

1. **SD vzor** — základňa 1–3 malých sviečok a za ňou silný odchod (telo ≥ 1,5 × ATR). Dopyt je pod cenou, ponuka nad ňou.
2. **Vrchol volume profilu** — v zóne leží riadok s najväčším objemom (POC) alebo iný vrchol (PEAK) profilu posledných 50 sviečok.
3. **Nárast klasického objemu** — sviečka s objemom aspoň 2 × priemer; stratégia sa od nej vráti na začiatok pohybu a zónou je tichá základňa pred ním. Takéto zóny sú na grafe **čierne**.

Zóna vznikne, len keď sa zhodnú aspoň **dve** z nich (`minConf`). Aktívne sú najviac 3 zóny na každej strane; keď príde nová, ustúpi tá najďalej od ceny.

## Ako vznikne obchod
Zóna platí, kým sa jej cena nedotkne. Prvý dotyk ju „zareže“ a ďalej ju sledujú už len modely IBS a pin bar:

- **Limit na zónu** — limit na bližšiu hranu neotestovanej zóny, stop za druhou hranou.
- **IBS** — rovnako ako stratégia IBS: gap proti smeru zóny → cena vyjde zo zóny → potvrdenie zatvorením → návrat k otvoreniu imbalance sviečky, tam limit. Stop za posledným swingom.
- **Pin bar** — sviečka s dlhým knôtom v zóne v smere obchodu, vstup hneď, stop za knôtom.

Cieľ je násobok rizika (`rrRatio`, predvolene 1 : 1). Každá zóna dá najviac jeden obchod a naraz beží najviac jeden obchod.

## Filtre
VWAP (long nad / short pod, alebo naopak; reset deň, otvorenie New Yorku, týždeň, mesiac), seansa New York, odstup medzi obchodmi, vek a kvalita zóny, max. riziko — všetko voliteľné.

## Slovníček
- **SD zóna (supply / demand)** — pásmo, odkiaľ cena predtým silno odišla.
- **Volume profil** — koľko sa zobchodovalo na ktorej cene; **POC** je cena s najväčším objemom.
- **Imbalance (gap)** — medzera medzi 1. a 3. sviečkou trojice, znak rýchleho pohybu.
- **RR** — pomer cieľa k stopu; RR 1 = cieľ rovnako ďaleko ako stop.
