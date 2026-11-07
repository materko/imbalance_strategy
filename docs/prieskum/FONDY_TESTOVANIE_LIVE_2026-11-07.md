# Ako testujú a spúšťajú stratégie fondy — a čo z toho pre TradeBot (7. 11. 2026)

Bod 8 týždenného zadania (31. 10.–8. 11. 2026): na internete hľadať, ako testovanie a ostré spúšťanie stratégií robia
fondy a banky (Citadel a podobní), a porovnať to s našou smernicou. Veľké fondy svoj postup nezverejňujú. Spoľahlivé
zdroje sú najmä akademické práce ich ľudí (Man AHL, AQR, López de Prado) a novinárske správy o multi-manager fondoch.
Z Citadelu a Two Sigma sú verejné len inzeráty a správy, nie pravidlá. Zdroje sú na konci.

## 1. Čo robia — sedem zistení

1. **Počet skúšok zvyšuje latku.** Harvey a Liu (Man Group, *Backtesting*, JPM 2015) ukazujú, že Sharpe zo spätného
   testu treba prepočítať podľa počtu vyskúšaných variantov. Pri ~300 testoch spadne t-štatistika 3,0 na ~2,0.
   Zrážka nie je paušálna: silné výsledky sa zrazia málo, hraničné veľa. Pravidlo „Sharpe deleno dvomi“ autori
   označujú za chybu. Bežná latka pre skutočný edge je t-štat ~3 namiesto 1,96.
2. **Deflated Sharpe a PBO.** Bailey a López de Prado navrhli dva nástroje:
   - Deflated Sharpe Ratio: Sharpe opravený o výber z mnohých skúšok a o nenormálne rozdelenie výnosov.
   - Pravdepodobnosť preladenia (PBO, metóda CSCV): ako často najlepší variant z ladenia skončí mimo vzorky
     pod mediánom ostatných.

   Porovnávacia štúdia zistila, že walk-forward falošné objavy filtruje slabšie ako kombinatorická očistená
   krížová validácia (CPCV).
3. **Naživo je to vždy horšie.**
   - V štúdii 215 bankových „alternative beta“ stratégií klesol Sharpe zo spätného testu naživo v mediáne o 73 %.
     Zložitejšie stratégie dopadli horšie.
   - Analýza 1 726 predávaných stratégií (2026) odhaduje, že živý výsledok zaostáva za spätným testom o ~2–3 % ročne.
     Hlavné príčiny sú zmena režimu trhu a preplnenie stratégie.
   - McLean a Pontiff pri publikovaných anomáliách: ~10 % poklesu je štatistický šum mimo vzorky, ďalších ~25 % pribudne
     po zverejnení.
4. **Multi-manager fondy (Millennium, Citadel) majú tvrdé pravidlá prepadu.**
   - Tím má vlastný rozpočet rizika a pevný limit prepadu, typicky **5 % od vrcholu**. Vtedy sa mu často zoberie
     polovica kapitálu.
   - Pri **~5–7,5 %** sa tím zatvára.
   - Citadel má riziko a výskum centralizovanejšie, Millennium necháva tímy samostatnejšie.

   Ide o pravidlá správania, nie o ďalší spätný test: limit je určený vopred a nediskutuje sa o ňom.
5. **Cesta z výskumu do produkcie je inžinierska práca.** Citadel v inzerátoch opisuje malé tímy, ktoré nápad prevedú
   do „production-grade“ kódu s krátkym cyklom. Výskumník robí koncept, spätný test aj živé nasadenie, model
   sa prepisuje do rýchleho produkčného kódu. U nás to zodpovedá C# jadru a parite bar po bare s Pythonom.
6. **Diverzifikácia cez štýly.** AQR (*Craftsmanship Alpha*, multi-style) ukazuje, že kombinácia viacerých nekorelovaných
   štýlov dáva robustnejšie portfólio ako jeden štýl. Samotné prevedenie (aké metriky, ako sa kombinujú) je
   podľa nich zdrojom výnosu.
7. **Veľkosť podľa volatility.** Harvey, Hoyle, Rattray a spol. (Man AHL, JPM 2018) ukazujú, že škálovanie pozície
   nepriamo k volatilite zlepšuje Sharpe a znižuje chvostové riziko, najmä pri akciových indexoch.
   Kritika: varianty s mesačným oknom (Moreira–Muir) mali v práci pohľad dopredu. Cieľom volatility targetingu je
   pokojnejšia krivka, nie vyšší výnos.

## 2. Ako na tom sme (smernica TradeBot)

| čo robia fondy | u nás | stav |
|---|---|---|
| odložené dáta mimo ladenia | odložený rok 9/2025–9/2026, spustený raz | ✓ |
| plató namiesto jedného bodu | susedia ≥ 80 % PF (krok 5) | ✓ |
| iný trh / iné dáta | krok 8 (NAS100, US500, XAU Dukascopy) | ✓ |
| vyššie náklady, oneskorenie | krok 9: 2× poplatok, vstup o sviečku neskôr | ✓ |
| zrážka za počet skúšok | Deflated Sharpe v kroku 9 len ako informácia; hľadanie skúša 15–35 tisíc kombinácií na stratégiu | ⚠ chýba v rozhodovaní |
| PBO / CSCV | nemáme | ✗ |
| vopred dané pravidlo vypnutia | krok 10 „ostrá prevádzka s pravidlom na vypnutie“ — číslo nie je dané | ⚠ |
| očakávanie poklesu naživo | porovnanie naživo vs. test na karte Live (pásmo 5–95 %) | ✓ čiastočne |
| sklz a neplnené limitky | poplatok 0,0018 %; sklz ticky nie; limitka sa v emulátore plní pri dotyku | ⚠ |
| nekorelované portfólio | karta Diverzifikácia (korelácia denných výsledkov) | ✓, nepoužíva sa pri výbere |
| veľkosť podľa volatility | riskDollar a stop v ATR | ✓ čiastočne |

## 3. Čo odporúčam zaviesť (poradie podľa prínosu)

1. **Pravidlo vypnutia pred každým live nasadením.** Číslo dať vopred do profilu nasadenia:
   - **vypnúť**, keď prepad naživo prekročí 95. percentil Monte Carlo prepadu z testu (checkup ho už počíta);
   - **polovičná veľkosť**, keď je výsledok naživo 20 obchodov po sebe pod 5. percentilom pásma „naživo vs. test“
     (karta Live ho už kreslí).

   Ide o tú istú myšlienku ako 5 % limit v multi-manager fondoch, len odvodená zo štatistiky samotnej stratégie.
2. **Rátať s poklesom naživo.** Plánovať zisk s polovičným edge: očakávaný PF naživo ≈ 1 + (PF z testu − 1) / 2.
   Stratégia z testu s PF 1,4 sa teda plánuje ako PF ~1,2. Trieda A auditu je preto latka na forward test, nie sľub.
3. **Počet skúšok do rozhodnutia.** Z gl_state poznáme počet kombinácií na stratégiu. Do auditu pridať zrážku
   Harvey–Liu (alebo Deflated Sharpe s reálnym počtom skúšok) ako podmienku triedy A, nie len informáciu.
4. **PBO (CSCV) ako krok 9b.** Rozdeliť 4 roky ladenia na 8 blokov, prejsť kombinácie 4 z 8 a zistiť, ako často
   víťaz z ladenia skončí pod mediánom na zvyšku. Kandidáti už majú obchody, takže je to lacný výpočet.
   Stratégia s PBO > 0,5 nejde na live.
5. **Sklz v tickoch.** V emulátore k poplatku pridať 1 tick sklzu na stop a market (ES 0,25–1 tick podľa verejných
   meraní, pri správach viac). Limitku plniť až pri prekročení ceny o 1 tick, nie pri dotyku.
6. **Výber do live cez portfólio.** Z triedy A brať stratégie s nízkou koreláciou denných výsledkov:
   - rôzne trhy (MNQ, ES, MGC);
   - rôzne typy (trend, návrat k priemeru, udalosti ako SPRÁVY);
   - rôzne časy dňa.

   Karta Diverzifikácia to vie spočítať, stačí ju použiť ako krok výberu.
7. **Jednoduchosť.** Bankové štúdie ukazujú, že zložité stratégie strácajú naživo viac. Pri rovnakom PF uprednostniť
   nastavenie s menej zapnutými filtrami.

## Zdroje

- Bailey, Borwein, López de Prado, Zhu — [The Probability of Backtest Overfitting](https://papers.ssrn.com/abstract=2326253); balík [pbo (CRAN)](https://ftp.fau.de/cran/web/packages/pbo/vignettes/pbo.html)
- Bailey, López de Prado — [The Deflated Sharpe Ratio](https://papers.ssrn.com/abstract=2460551)
- Harvey, Liu — [Backtesting (Duke)](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF), [Man Group — Backtesting](https://www.man.com/insights/backtesting)
- Harvey, Hoyle a spol. — [The impact of volatility targeting](https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf); [Research Affiliates — Harnessing Volatility Targeting](https://www.researchaffiliates.com/content/dam/ra/publications/pdf/1014-harnessing-volatility-targeting.pdf)
- Pokles naživo — [arXiv 2604.18821](https://arxiv.org/pdf/2604.18821), [Harbourfront Quant](https://harbourfrontquant.substack.com/p/why-backtests-decay-regime-dependence), [Alpha Architect](https://alphaarchitect.com/beware-of-backtest-overfitting/), [Morningstar — On Back-Tests](https://tw.morningstar.com/tw/news/120401/on-back-tests-(part-2).aspx)
- AQR — [Craftsmanship Alpha](https://www.aqr.com/Insights/Research/Journal-Article/Craftsmanship-Alpha-An-Application-to-Style-Investing), [Multiple risk factors (ai-CIO)](https://ai-cio.com/news/aqr-multiple-risk-factors-are-better-than-one)
- Multi-manager fondy — [Nasdaq: Citadel, Millennium losses](https://www.nasdaq.com/articles/citadel-millennium-losses-expose-pod-shop-vulnerabilities), [Citadel is from Mars and Millennium is from Venus](https://rupakghose.substack.com/p/citadel-is-from-mars-and-millennium), [BNN Bloomberg: BlueCrest, Millennium pods](https://www.bnnbloomberg.ca/investing/2024/08/30/bluecrest-millennium-pods-faced-quick-closure-after-turmoil/)
- Citadel z inzerátov — [Quantitative Research Engineer](https://www.builtinnyc.com/job/quantitative-research-engineer-university-graduate-us/10064238)
- Sklz a medzera test vs. naživo — [NexusFi](https://nexusfi.com/a/automation/backtest-to-live-performance-gap), [LuxAlgo](https://luxalgo.com/blog/backtesting-limitations-slippage-and-liquidity-explained); pravidlá vypnutia — [backtest → paper → live](https://aifinhub.pages.dev/articles/backtest-to-paper-to-live-playbook/), [Kieran Duff](https://kieranduff-com.pages.dev/letters/your-trading-strategy-will-fail.html) (praktici, nie inštitúcie)
