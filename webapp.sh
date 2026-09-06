#!/usr/bin/env bash
# Spustí webovú aplikáciu pre testerov z koreňa repozitára (macOS / Linux).
# Tenký obal nad platforms/freqtrade/scripts/webapp.sh - viď docs/WEBAPP.md.
#
#   ./webapp.sh
#   TRADEBOT_WEB_PORT=9000 NO_BROWSER=1 ./webapp.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/platforms/freqtrade/scripts/webapp.sh" "$@"
