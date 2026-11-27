#!/bin/sh
# Plocha + iCloud (Python, kvôli oprávneniam macOS) a zamknutá stránka na GitHub Pages.
SRC=/Users/martin/IBS/.nightsearch
cd "$SRC" && ../.venv/bin/python glcopy.py
cd "$SRC" && ../.venv/bin/python glpublic.py build >/dev/null && cd dash/public && git add -A && git -c user.name=IBS -c user.email=mmkrissak@gmail.com commit -qm "Obnov vysledky $(date +%Y-%m-%d)" && git push -q
echo "stránka nahraná"
