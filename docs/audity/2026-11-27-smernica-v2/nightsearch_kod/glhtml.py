"""Len znovu poskladá stránku z hotových dát (dash/dashboard_data.json) a šablóny — bez prepočtu (po zmene vzhľadu)."""
import json, re
from pathlib import Path
D = Path("/Users/martin/IBS/.nightsearch/dash")
data = json.loads((D / "dashboard_data.json").read_text())
html = open("/Users/martin/IBS/tester/dashboard/index.html").read()
html = re.sub(r"<!doctype html>\s*", "", html, flags=re.I)
html = re.sub(r"</?html[^>]*>|</?head>|</?body>|<meta charset[^>]*>|<meta name=\"viewport\"[^>]*>", "", html)
html = html.replace("<title>Výsledky testovania</title>", "")
i = html.rfind("<script>")
payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
html = html[:i] + f"<script>window.DASHBOARD_DATA = {payload};</script>\n" + html[i:]
(D / "tradebot_vysledky.html").write_text("<title>TradeBot výsledky</title>\n" + html.strip() + "\n")
print("ok")
