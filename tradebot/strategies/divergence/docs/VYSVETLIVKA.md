# Divergence — ako funguje

> V jednej vete: stratégia hľadá **divergencie** (cena robí nové dno, ale indikátor už nie) a obchoduje ich len v smere trendu vyšších TF, pri pullbacku.

Je to prepis staršej Freqtrade stratégie z roku 2022.

## Ako vznikne obchod
1. Na grafe (Heikin Ashi sviečky) sa hľadajú **divergencie** na viacerých indikátoroch (RSI, MACD, stochastik, OBV…). Býčia divergencia: cena nižšie dno, indikátor vyššie dno → sila predajcov slabne.
2. **Trend** musí súhlasiť: Supertrend na 1h aj 4h ukazuje hore (pre long).
3. **Pullback**: Supertrend na grafe je proti (cena sa práve vracia).
4. Žiadna medvedia divergencia na vyšších TF (to by bol varovný signál).
5. Vstup buď hneď, alebo po potvrdzovacej sviečke (zavretie nad predošlou).

## Stop a cieľ
- Stop z ATR, voliteľný cieľ RR, dvojstupňový trailing (zámok zisku a sledovanie ceny).
- Stratový obchod sa zavrie, keď Supertrend na 4h otočí proti.

## Čo môžeš nastaviť
- Ktoré indikátory sa sledujú, koľko divergencií treba, RSI hranice, trailing, typ vstupu.

## Slovníček
- **Divergencia** — cena a indikátor idú opačne; často predchádza otočke.
- **Supertrend** — indikátor smeru trendu (čiara pod / nad cenou).
- **Heikin Ashi** — vyhladené sviečky, ktoré lepšie ukazujú trend.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe. Prahy v ATR fungujú rovnako na pokojnom aj divokom trhu.
