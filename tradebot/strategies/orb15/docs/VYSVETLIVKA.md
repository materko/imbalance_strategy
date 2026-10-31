# ORB 15/5 1.0 — ako funguje

> V jednej vete: prvých 15 minút New Yorku vytvorí rozpätie a prvá 5-minútová sviečka, ktorá zavrie za ním, otvorí obchod v smere prierazu.

Prepis Rust stratégie „15m Opening Range Breakout“ (roboquant.dev), ktorú poslal používateľ 29. 10. 2026.

## Opening range (OR)
- **OR** je high a low sviečok **9:30–9:45 NY** (15:30–15:45 u nás) — na 5m grafe tri sviečky.

## Kedy vstúpi
- Sviečka **zavrie nad high OR** → long, **pod low OR** → short; vstup trhom na zavretí.
- Najviac **1 obchod za deň**, nie po 16:00 NY.
- **Filter predošlého dňa:** keď je cena po OR pod low včerajška, longy sa v ten deň neberú; nad high včerajška shorty nie.
- Voliteľný **filter knôtu:** prieraz s veľkým knôtom proti smeru (napr. spodný knôt pri longu nad 50 % sviečky) sa preskočí.

## Stop a cieľ
- **Stop** na druhej strane OR (long pod low OR, short nad high OR).
- **Cieľ** 2 × vzdialenosť stopu (RR 2), alebo pevný počet bodov.
- Predloha pozíciu zatvára o 16:00 NY; pri testoch podľa smernice je to vypnuté.

## Rozdiely oproti predlohe
- Predloha má long aj short predvolene vypnuté (bez prepnutia neobchoduje); tu sú zapnuté.
- Predošlý deň = obchodný deň CME (od 18:00 NY), predloha berie dennú sviečku platformy.

## Slovníček
- **Prieraz zavretím** — rozhoduje cena zavretia sviečky, nie knôt.
- **RR** — pomer cieľa k stopu.
