# Gap Fill — ako funguje

> V jednej vete: keď trh otvorí inde, než včera zavrel (medzera, „gap“), stratégia stavia na to, že sa tá medzera zatvorí — gap hore predáva, gap dole kupuje.

Meranie na 2 791 dňoch NQ ukázalo, že malá medzera (pod 0,3 ATR) sa vyplní v ~78 % dní, s potvrdením prvej 15m sviečky až v ~93 %; veľká (nad 1,2 ATR) len v ~8 %.

## Ako vznikne obchod
1. Na prvej sviečke seansy sa zmeria **medzera** = dnešné otvorenie − včerajšie zavretie seansy.
2. Filtre: veľkosť medzery v ATR, smer, či otvorenie padlo do včerajšieho rozpätia.
3. Vstup **proti medzere** — hneď, po potvrdzovacej sviečke alebo na reteste.

## Stop a cieľ
- **Cieľ** = včerajšie zavretie (výplň medzery) alebo jej časť.
- **Stop** podľa nastavenia (default 1 ATR — z merania, ako ďaleko ide cena proti).
- Obchod končí na cieli, stope, po max. čase alebo na konci seansy.

## Čo môžeš nastaviť
- Min. / max. veľkosť medzery (ATR), smer, typ vstupu, stop, podiel výplne ako cieľ, max. dĺžka držania.

## Slovníček
- **Gap (medzera)** — rozdiel medzi včerajším zavretím a dnešným otvorením.
- **ATR** — priemerný rozsah sviečky; meria, ako veľmi sa trh hýbe.
