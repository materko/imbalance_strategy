#!/usr/bin/env bash
# Spustí webovú aplikáciu pre testerov z koreňa repozitára (macOS / Linux).
# Tenký obal nad tester/scripts/webapp.sh - viď docs/WEBAPP.md.
#
#   ./webapp.sh
#   TRADEBOT_WEB_PORT=9000 NO_BROWSER=1 ./webapp.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tester/scripts/webapp.sh" "$@"
