# Big 7 + SOXX — vysvetlivky k panelu

Ku skriptu [big7_basket_ema.pine](big7_basket_ema.pine). Ladené na čierne pozadie.

---

## 1. Čo to vlastne počíta

Panel nekreslí cenu. Kreslí **skóre smeru od −100 do +100**, ktoré vzniká zlúčením
piatich nezávislých pohľadov na to isté:

| zložka | čo meria | ako sa normalizuje |
|---|---|---|
| **Kôš** | vážený priemer percentuálnych zmien siedmich mega-capov | ±100 pri `Kôš / SOXX: plné skóre pri (%)` |
| **Trend** | sklon EMA nad košom, za jednu sviečku | ±100 pri `Trend: plné skóre pri sklone` |
| **Šírka** | `(hore − dole) / počet` — koľko zo siedmich ide tým istým smerom | prirodzene ±100 |
| **SOXX** | percentuálna zmena polovodičov | ±100 pri tom istom prahu ako kôš |
| **Vedenie** | `kôš % − index %` — o koľko mega-capy prekonávajú index | ±100 pri `Vedenie: plné skóre pri rozdiele (%)` |

Každá má vlastnú váhu. **Chýbajúci feed vypadne aj z menovateľa** — keď jeden ticker mlčí,
neráta sa ako nula, ale akoby tam nebol. To isté platí pre samotný kôš.

Percentá sa počítajú od denného ukotvenia: buď od **včerajšieho zavretia** (denná zmena
vrátane nočnej medzery), alebo od **dnešného otvorenia** (len pohyb v seanse). Prepína sa
v *Percentá počítať od*.

---

## 2. Čo je čo na obrazovke

Farby určuje *Paleta*: **Neón** (cyan hore, magenta dole — predvolené, na čiernom pozadí
svieti) alebo **Klasika** (zelená / červená).

| prvok | vzhľad | čo znamená |
|---|---|---|
| **Vyplnená plocha** | cyan hore, magenta dole | smer. Sýtosť rastie **plynule** s tým, ako ďaleko je skóre od nuly — nie skokom na prahu |
| **Žiara okolo čiary** | rozmazaný neónový okraj | len vzhľad. Tri vrstvy tej istej čiary, každá širšia a priesvitnejšia. Vypína sa v *Žiara okolo čiary* |
| **Hrubá čiara** | cyan / magenta | samotné skóre. Toto je jediná hodnota, ktorá je aj v hlavičke panelu |
| **Histogram** | stĺpce | alternatíva k ploche, zapína sa v *Tvar skóre*. Stĺpce sa rozsvecujú s presvedčivosťou |
| **Dve vodorovné čiary** | zelená hore, červená dole | prahy `±Prah skóre`. Za nimi môže vzniknúť signál |
| **Tenká čiara v strede** | sivomodrá | nula |
| **Pásik štvorčekov pri spodnej hrane** | zelené / červené | stav bar po bare. Prázdne miesto = bez smeru alebo mimo burzových hodín |
| **Podfarbené pozadie** | slabo zelené / červené | ten istý stav, na periférne videnie. Vypína sa v *Podfarbiť pozadie podľa stavu* |
| **Tmavosivé pozadie** | šedé | mimo 9:30–16:00 New York |
| **Štítok LONG / SELL na čiare** | cyan / magenta so šípkou | okamih **otočenia**. Nie „stále platí", ale „práve teraz sa to zmenilo" |
| **Štítok LONG / SELL pri sviečke** | na hlavnom grafe | ten istý signál, nakreslený priamo k cene. Vypína sa v *Značky aj na cenovom grafe* |
| **Veľká visačka na konci čiary** | zelená / červená / sivá | aktuálny stav. Toto je odpoveď na otázku „kam teraz" |
| **▲ oranžový trojuholník pri hornej hrane** | | úzky ťah alebo slabá šírka |
| **◆ fialový kosoštvorec pri hornej hrane** | | polovodiče idú proti košu |

### Rozdiel medzi štítkom a visačkou

**Štítok `LONG`** na čiare je udalosť — v tom mieste sa stav otočil. Za deň ich býva jeden
až tri.

**Visačka** na pravom konci je stav — čo platí **teraz**. Je tam vždy, aj keď sa dnes nič
neotočilo, a môže ukazovať `LONG`, `SELL`, `BEZ SMERU` alebo `MIMO HODÍN`.

---

## 3. Tabuľka

Zoradená tak, že **to najdôležitejšie je hore** — na nízkom paneli sa tabuľka odrezáva
zdola, tak nech prežije to, kvôli čomu sa na ňu pozeráš.

| riadok | čo je to |
|---|---|
| **SMER** | výsledok, celý riadok na farebnom pozadí: `LONG` / `SELL` / `BEZ SMERU` / `MIMO HODÍN` |
| **skóre** | číslo −100…+100, veľkým písmom, vo farbe smeru |
| **šírka** | `koľko je hore / koľko má dáta`. Zelené, keď je splnené `Min. titulov na strane signálu` |
| KÔŠ | vážený priemer siedmich titulov |
| SOXX | polovodiče |
| QQQ | index na porovnanie |
| sedem tickerov | percentuálna zmena každého titulu |

`Tabuľka — rozsah` určuje, koľko riadkov sa kreslí:

| rozsah | riadkov | obsahuje |
|---|---|---|
| Len smer | 1 | `SMER` |
| Kompaktná | 3 | + skóre, šírka |
| **Stredná** (predvolené) | 6 | + kôš, SOXX, index |
| Plná | 13 | + všetkých sedem titulov |

`Tabuľka — kde` ju postaví do ktoréhokoľvek zo štyroch rohov panelu.

---

## 4. Kedy vznikne signál

Stav sa otočí na `LONG`, až keď platí **všetko naraz**:

1. skóre je **nad prahom** (`Prah skóre`)
2. aspoň `Min. titulov na strane signálu` zo siedmich je v pluse
3. SOXX je v pluse — ak je zapnuté `SOXX musí súhlasiť`
4. drží to `Potvrdiť N sviečok` po sebe
5. je po `Preskočiť prvých N sviečok dňa`
6. je v rámci 9:30–16:00 New York — ak je zapnuté `Len počas burzových hodín`

`SELL` je presné zrkadlo. Stav sa mení **až na zavretí sviečky**, takže indikátor
neprekresľuje; vypína sa to v *Signál až na zavretí sviečky*.

### Kedy stav zanikne

Stav nie je len o vzniku signálu — musí aj **zaniknúť**, inak drží starý smer, kým sa
nepotvrdí opačný. A keď sa opačný nepotvrdí (napríklad preto, že SOXX má veto), pozadie
svieti starou farbou celé hodiny, hoci skóre je dávno na druhej strane.

`Stav vynulovať` na to má štyri voľby:

| voľba | stav zanikne |
|---|---|
| Pri prechode cez nulu | keď skóre prejde na opačnú stranu nuly |
| Na začiatku dňa | každé ráno; včerajší názor nehovorí o dnešku |
| **Oboje** (predvolené) | obe podmienky naraz |
| Nikdy | pôvodné správanie — drží, kým nepríde opačný signál |

Vynulovaný stav je **`BEZ SMERU`**, nie opačný signál. Starý smer už neplatí, nový ešte
nevznikol.

### Prečo je stav niekedy `BEZ SMERU`, hoci skóre je vysoké

Skóre je priemer. Môže byť +60 aj vtedy, keď sú v pluse len štyri tituly zo siedmich
a šírka podmienku nesplní. Alebo SOXX klesá a má veto. Práve o to ide — **skóre nie je
signál, je to jedna z podmienok.**

---

## 5. Varovania

| značka | podmienka | čo znamená |
|---|---|---|
| ▲ | vedenie je takmer na maxime, ale index sa takmer nehýbe | **úzky ťah** — nesú to mega-capy, zvyšok trhu nejde s nimi |
| ▲ | kôš je silný, ale šírka slabá | **pár mien ťahá priemer**, skupina nie je zajedno |
| ◆ | SOXX a kôš majú opačné znamienko a oba sú dosť ďaleko od nuly | **polovodiče idú proti** — historicky skôr varovanie než príležitosť |
| ⚡ | kôš sa pohol o viac než `Impulz: koľko sigma` za `Impulz: okno` | **trh na niečo reaguje** — cena po správe skáče, nedriftuje |
| ✦ | VIX vyskočil nad `VIX: skok od (%)` | **trh dostal strach** |

Varovania platia len počas burzových hodín a len keď má indikátor vôbec názor. Pred
otvorením stoja všetky tituly presne na svojom ukotvení, percentá sú nuly a z porovnávania
núl vychádza „nesúhlas", ktorý nič neznamená.

---

## 5b. Blok „Reakcia na správy"

**Pine nevie prečítať text správy** — žiadne API na to v TradingView nie je. Vie však
prečítať, ako trh na správu reaguje, a to sa dá rozobrať na tri merateľné veci.

### Rozptyl — odkiaľ správa prišla

Vážená smerodajná odchýlka siedmich percent okolo koša, vydelená veľkosťou pohybu koša.

| hodnota | znamená |
|---|---|
| **nízka** (pod `Rozptyl: pod týmto je to makro`) | všetkých sedem ide spolu → za tým je **makro** správa: CPI, Fed, clá, dáta z trhu práce. Smer koša je vtedy dôveryhodný |
| **vysoká** (nad `Rozptyl: nad týmto ťahá jeden titul`) | pole je roztiahnuté → ťahá to **jeden titul**: earnings, žaloba, produkt. Priemer vtedy o skupine nehovorí takmer nič |

Toto je presne ten prípad, keď je META +6,9 % a zvyšok okolo +0,5 %: kôš vyzerá silne,
ale je to správa o jednej firme. Vysoký rozptyl preto spúšťa aj varovanie ▲.

### Impulz — ako tvrdo to dopadlo

O koľko sigma sa kôš pohol za posledných `Impulz: okno` sviečok oproti tomu, ako sa
hýbal doteraz. Správa sa v cene prejaví ako **náhly skok**, nie ako plynulý drift.

### VIX — či trh dostal strach

Index strachu skáče na headlinoch skôr, než sa stihne prečítať, čo sa vlastne stalo.
Voliteľne (`VIX blokuje LONG`) vie zablokovať LONG signál — len LONG, lebo strach je
asymetrický a rastúci VIX pádom neprekáža. Predvolene je to **vypnuté**: blok správ má
najprv informovať, nie rozhodovať.

### Riadok „správy" v tabuľke

| text | znamená |
|---|---|
| `pokoj` | nič mimoriadne |
| `makro` | sedmička ide spolu, ale bez náhleho skoku |
| `jeden titul` | pole je roztiahnuté, priemer je zavádzajúci |
| `IMPULZ ⚡` | náhly pohyb, pôvod nejasný |
| `MAKRO ⚡` | náhly pohyb a všetci idú spolu — najsilnejší prípad, smer sa dá brať vážne |
| `JEDEN TITUL ⚡` | náhly pohyb, ale ťahá ho jedna firma — smer koša neznamená smer trhu |
| `VIX SKOK` | strach prebíja všetko ostatné |

### Čo tento blok nevie

Nevie, **o akú správu ide ani či je dobrá**. Vie len povedať, že trh sa práve pohol
netypicky, či sa hýbu všetci naraz, a či stúpa strach. Na zistenie, čo sa stalo,
potrebuješ kalendár alebo terminál — na to Pine nestačí.

---

## 6. Zložky skóre (zapína sa v *Kresliť zložky skóre*)

Štyri tenké čiary v mierke skóre. Ukážu, ktorá zložka skóre ťahá a ktorá mu odporuje.

| farba | zložka |
|---|---|
| **žltá**, schodíková | šírka |
| **fialová** | SOXX |
| **oranžová** | vedenie |
| **zelenkavá** | trend |

Piata zložka (kôš) je samotná hlavná čiara v režime *Percentá koša*.

Zapni si ich na prvý týždeň. Uvidíš, ktorá zložka rozhoduje a ktorá len šumí — a podľa
toho jej zmeníš váhu.

---

## 7. Dva režimy

Prepína sa v *Čo kresliť*. Skóre a percentá majú úplne inú mierku, preto sa nekreslia naraz.

- **Skóre smeru** (−100…+100) — hlavný pohľad, toto sleduj
- **Percentá koša** (%) — kôš a jeho EMA, keď chceš vidieť surové čísla

---

## 8. Ako to používať

Nie je to spúšťač vstupu. Je to **smerová brána** nad tvojimi stratégiami:

| stav | čo s tým |
|---|---|
| `LONG` | z ORB alebo Breakout ber len prerazenia nahor |
| `SELL` | len nadol |
| `BEZ SMERU` | deň bez smeru — menšia veľkosť alebo nič |
| `MIMO HODÍN` | indikátor nemá názor, akciové feedy stoja |
| ▲ alebo ◆ | signál stojí na pár menách — zníž veľkosť alebo počkaj |

---

## 8b. Vzhľad

| nastavenie | čo robí |
|---|---|
| **Paleta** | Neón (cyan / magenta) alebo Klasika (zelená / červená) |
| **Tvar skóre** | Plocha, Histogram alebo Oboje |
| **Žiara okolo čiary** | neónový efekt — tri vrstvy čiary nad sebou |
| **Značky aj na cenovom grafe** | LONG/SELL sa kreslí aj k sviečkam, nielen do panelu |
| **Podfarbiť pozadie podľa stavu** | jemný farebný nádych celého panelu |
| **Tabuľka — rozsah / kde** | koľko riadkov a v ktorom rohu |

Značky na cenovom grafe používajú `force_overlay`. Keby ich tvoja verzia TradingView
nepoznala a skript hlásil chybu, zmaž tie dva riadky — sú v kóde označené a nič iné
na nich nevisí.

---

## 9. Hlavička panelu

V hlavičke je jediná hodnota — **skóre**. Všetko ostatné je `display.pane`: kreslí sa,
ale do hlavičky nelezie, takže tam neostávajú prázdne `∅`.

Dlhý zoznam čísel za názvom (`9 1 1 1 1 0.5 …`) je TradingView, nie skript. Vypneš ho:
pravým na panel → **Settings → Status line → Arguments**.

---

## 10. Čo tento nástroj nevie

**Nie je odmeraný.** V našom archíve nemáme dáta jednotlivých akcií, takže sa nedal
prehrať ani vo Freqtrade, ani v emulátore MultiCharts. Prahy a váhy sú odvodené z toho,
ako sa tie veličiny správajú, nie z výsledku testu. Ber ho ako kontext, nie ako model.

Čo by bolo treba na to, aby sa dal zmerať, je v [README.md](README.md).
