"""Verejná stránka s výsledkami chránená menom a heslom (bez Claude účtu).

    python glpublic.py pridaj <meno>    # heslo sa zadá v termináli, nikde sa neukladá
    python glpublic.py odober <meno>
    python glpublic.py zoznam
    python glpublic.py build            # dash/public/index.html z dash/tradebot_vysledky.html

Ako to funguje: celý dashboard je zašifrovaný (AES-256-GCM) jedným hlavným kľúčom
(dash/.master_key, nikam sa nenahráva). Pre každý prístup je v stránke hlavný kľúč
zašifrovaný kľúčom odvodeným z „meno:heslo" (PBKDF2-SHA256, 310 000 iterácií). Bez
správneho mena a hesla sa zo stránky nedá prečítať nič. Heslá sa neukladajú nikde.
Odobratie prístupu: `odober` a potom `rotuj` (nový hlavný kľúč; ostatným treba prístup
pridať znova), inak si odobratý človek mohol hlavný kľúč odložiť.
"""
import base64, getpass, gzip, json, os, sys, time
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib

D = Path("/Users/martin/IBS/.nightsearch/dash")
KEYF, USERS, OUT = D / ".master_key", D / "pristupy.json", D / "public"
ITER = 310_000
b64 = lambda b: base64.b64encode(b).decode()


def master():
    if not KEYF.exists():
        KEYF.write_bytes(os.urandom(32)); os.chmod(KEYF, 0o600)
    return KEYF.read_bytes()


def users():
    return json.loads(USERS.read_text()) if USERS.exists() else {}


def add(name):
    pw = getpass.getpass(f"Heslo pre {name}: ")
    if len(pw) < 8 or pw != getpass.getpass("Zopakuj heslo: "):
        sys.exit("Heslá sa nezhodujú alebo sú kratšie než 8 znakov.")
    salt, iv = os.urandom(16), os.urandom(12)
    k = hashlib.pbkdf2_hmac("sha256", f"{name.strip().lower()}:{pw}".encode(), salt, ITER, 32)
    u = users(); u[name.strip().lower()] = {"s": b64(salt), "i": b64(iv), "k": b64(AESGCM(k).encrypt(iv, master(), None))}
    USERS.write_text(json.dumps(u, indent=1)); print(f"Prístup {name} pridaný. Spusti build (alebo počkaj na ranné obnovenie).")


PAGE = """<!doctype html>
<html lang="sk"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>TradeBot výsledky</title>
<style>
:root{--bg:#f4f6f9;--card:#fff;--fg:#111827;--mut:#5f6b7a;--bd:#e1e6ed;--ac:#2563eb;--neg:#dc2626}
@media (prefers-color-scheme:dark){:root{--bg:#0b0f14;--card:#121821;--fg:#e7edf4;--mut:#8a97a8;--bd:#232d3a;--ac:#3b82f6;--neg:#ef4444;color-scheme:dark}}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;padding:0 16px}
form{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:28px;width:100%;max-width:340px;display:grid;gap:12px;box-sizing:border-box}
h1{margin:0;font-size:20px}h1 span{color:#22c55e}p{margin:0;color:var(--mut);font-size:13px}
label{display:grid;gap:4px;font-size:13px;color:var(--mut)}
input{font:inherit;padding:10px 12px;border:1px solid var(--bd);border-radius:8px;background:var(--bg);color:var(--fg)}
button{font:inherit;font-weight:600;padding:10px;border:0;border-radius:8px;background:var(--ac);color:#fff;cursor:pointer}
#err{color:var(--neg);min-height:1.2em}
</style></head><body>
<form id="f"><h1>Trade<span>Bot</span> výsledky</h1><p>Prihlás sa menom a heslom, ktoré si dostal.</p>
<label>Meno<input id="u" autocomplete="username" required></label>
<label>Heslo<input id="p" type="password" autocomplete="current-password" required></label>
<button id="b">Prihlásiť</button><p id="err"></p></form>
<script>
var V=__VAULT__;
function d64(s){return Uint8Array.from(atob(s),function(c){return c.charCodeAt(0)})}
async function open_(mk){
  var key=await crypto.subtle.importKey("raw",mk,"AES-GCM",false,["decrypt"]);
  var z=await crypto.subtle.decrypt({name:"AES-GCM",iv:d64(V.iv)},key,d64(V.data));
  var html=await new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
  try{sessionStorage.setItem("tbk",btoa(String.fromCharCode.apply(null,new Uint8Array(mk))))}catch(e){}
  document.open();document.write(html);document.close();
}
async function login(name,pw){
  var u=V.users[name.trim().toLowerCase()];if(!u)return null;
  var base=await crypto.subtle.importKey("raw",new TextEncoder().encode(name.trim().toLowerCase()+":"+pw),"PBKDF2",false,["deriveKey"]);
  var k=await crypto.subtle.deriveKey({name:"PBKDF2",salt:d64(u.s),iterations:V.it,hash:"SHA-256"},base,{name:"AES-GCM",length:256},false,["decrypt"]);
  try{return await crypto.subtle.decrypt({name:"AES-GCM",iv:d64(u.i)},k,d64(u.k))}catch(e){return null}
}
document.getElementById("f").addEventListener("submit",async function(e){
  e.preventDefault();var b=document.getElementById("b"),er=document.getElementById("err");b.disabled=true;er.textContent="Overujem…";
  var mk=await login(document.getElementById("u").value,document.getElementById("p").value);
  if(!mk){er.textContent="Nesprávne meno alebo heslo.";b.disabled=false;return}
  try{await open_(mk)}catch(x){er.textContent="Stránku sa nepodarilo otvoriť (prehliadač je príliš starý?).";b.disabled=false}
});
(async function(){try{var s=sessionStorage.getItem("tbk");if(s)await open_(d64(s))}catch(e){try{sessionStorage.removeItem("tbk")}catch(_){}}})();
</script></body></html>
"""


def build():
    u = users()
    if not u:
        sys.exit("Najprv pridaj aspoň jeden prístup: python glpublic.py pridaj <meno>")
    body = (D / "tradebot_vysledky.html").read_text()
    full = ('<!doctype html>\n<html lang="sk"><head><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width, initial-scale=1">\n' + body + "\n</html>\n")
    iv = os.urandom(12)
    data = AESGCM(master()).encrypt(iv, gzip.compress(full.encode(), 9), None)
    vault = {"it": ITER, "iv": b64(iv), "data": b64(data), "users": u}
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(PAGE.replace("__VAULT__", json.dumps(vault)))
    (OUT / ".nojekyll").write_text("")
    print("hotovo", OUT / "index.html", round((OUT / "index.html").stat().st_size / 1e6, 2), "MB,", len(u), "prístupov,", time.strftime("%H:%M"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "pridaj" and len(sys.argv) > 2:
        add(sys.argv[2])
    elif cmd == "odober" and len(sys.argv) > 2:
        u = users(); u.pop(sys.argv[2].strip().lower(), None); USERS.write_text(json.dumps(u, indent=1)); print("odobraté")
    elif cmd == "zoznam":
        print("\n".join(users()) or "(žiadne)")
    elif cmd == "rotuj":
        KEYF.unlink(missing_ok=True); USERS.unlink(missing_ok=True); print("Nový kľúč; všetky prístupy treba pridať znova.")
    else:
        build()
