#!/bin/sh
# Ranná obnova výsledkov (launchd 6:00): tabuľka do iCloudu, dashboard, nové nastavenia do histórie Labu,
# priečinok na ploche + iCloud, zamknutá web stránka na GitHub Pages.
cd /Users/martin/IBS/.nightsearch || exit 1
PY=../.venv/bin/python
# SMERNICA V2 (používateľ 27. 11. 2026): výsledky vymazané, nové až po dokončení programovania — kým existuje dash/V2_cakam, ranné nahrávanie nič negeneruje ani nepublikuje
[ -f dash/V2_cakam ] && { echo "$(date) V2_cakam: ranné nahrávanie preskočené (výsledky sa nahrajú až po zavedení V2)" >> dash/morning.log; exit 0; }
# gl_stop_after_morning (jednorazovo, používateľ): testy zastaviť natrvalo (gl_paused) a len nahrať výsledky
# Bežia testy? (pred pozastavením) Keď nie, poradie a čísla nastavení ani profily vo webapp sa NEMENIA
# (používateľ 16. 10. 2026: „ráno nemeň poradie stratégií, keď nebežia žiadne testy“ — live nasadenia sa odvolávajú na profily).
TESTS=""
for p in $(pgrep -f "glsearch.py|glhyper.py|glhub.py|glrr.py"); do
  [ "$(ps -o stat= -p $p | cut -c1)" != "T" ] && TESTS=1
done
# testy bežali od minulého ranného nahrávania (napr. zastavené o 5:00) — výsledky sa nahrajú ako pri bežiacich testoch
[ -n "$(find gl_state.json hyper_state.json hub_state.json rr_state.json -newer dash/.last_morning 2>/dev/null)" ] && TESTS=1
[ -f dash/.last_morning ] || TESTS=1
# Testy sa počas nahrávania NEpozastavujú (používateľ 14. 11. 2026: nahrávanie trvalo hodinu a hub celý ten čas stál);
# stav sa zapisuje atómovo, nahrávanie berie čísla z okamihu čítania.
if [ -f gl_stop_after_morning ]; then ./glpause.sh stop; rm -f gl_stop_after_morning; STOP_ALL=1; fi
# glrr (zadanie používateľa) beží aj keď sú testy pozastavené — okrem jednorazového zastavenia po nahratí
trap './glpause.sh mcont; [ -z "$STOP_ALL" ] && pkill -CONT -f glrr.py' EXIT
{ date
  (cd .. && git pull --rebase --autostash -q) || echo "git pull zlyhal — generujem zo starej šablóny"   # nová šablóna stránky (tester/dashboard) pred generovaním
  [ -n "$TESTS" ] && $PY glrr_morning.py             # IBS EZ s vyšším RR (glrr na hube): najlepšie doteraz → plató + odložený rok → kandidáti
  $PY glreport.py
  $PY gldash.py
  ./glcopy.sh                      # stránka, plocha, iCloud hneď — až potom pomalšie behy do histórie
  if [ -n "$TESTS" ]; then
  $PY gldash_runs.py
  $PY glsmernice.py --apply        # SMERNICE: pri stratégii s prejdeným nastavením len prejdené profily a behy
  $PY glwebvyber.py --apply        # webapp: navrchu prešli smernicou + Sortino, max 3 profily (používateľ 8. 11.)
  sh glwebcheckup.sh               # Výkon (analytika) pre profily webapp, ktorým chýba
  $PY glcheckup_missing.py         # krok 7: analytika pre nové / zmenené prejdené nastavenie č. 1
  $PY glnas100_missing.py          # krok 8: iný trh (NAS100 / XAU) pre nové / zmenené nastavenie č. 1
  $PY glrobust_missing.py          # krok 9 (len informácia): robustnosť pre nové / zmenené nastavenie č. 1
  $PY glwr_steps.py               # kroky 7–9 aj pre TOP AS 75 (nastavenie č. 1 každej wr stratégie, 12. 11. 2026)
  $PY gldash.py && ./glcopy.sh     # stránka znova, aby kroky 7–9 boli vidieť hneď (nie až na druhý deň)
  else echo "testy nebežia — poradie, čísla a profily nastavení ostávajú bez zmeny"; fi
  (cd .. && .venv/bin/python -m tester.webapp.cli push)
  # výber webapp (glwebvyber) cli push nenesie — bez neho ostatné stroje nevidia nové profily (16. 11. 2026)
  (cd .. && if ! git diff --quiet -- tester/webapp_vyber.json; then
     git commit -q -m "Aktualizuj výber profilov vo webapp podľa stránky výsledkov" -- tester/webapp_vyber.json &&
     git pull -q --rebase --autostash && git push -q && echo "výber webapp pushnutý"; fi)
  touch dash/.last_morning
  echo hotovo; } >> dash/morning.log 2>&1
