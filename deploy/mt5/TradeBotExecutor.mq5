//+------------------------------------------------------------------+
//| TradeBotExecutor - vykonavac orderov pre strategiu, ktora bezi v NinjaTraderi (docs/ROUTING.md)    |
//|                                                                                                   |
//| Ziadna strategia: prikazy cita z Common\Files\TradeBot\bridge\ a vykona ich na tomto ucte. Jeden    |
//| na MT5 ucet, na lubovolnom grafe (obchoduje vsetky symboly route). Instalacia:                     |
//|                                                                                                   |
//|     python -m tradebot.adapters.mt5 install                                                       |
//|                                                                                                   |
//| V terminali musi byt Tools > Options > Expert Advisors > Allow DLL imports a zapnuty Algo Trading.  |
//| Len hedging ucet.                                                                                  |
//+------------------------------------------------------------------+
#include <TradeBot/TradeBotExecutor.mqh>
