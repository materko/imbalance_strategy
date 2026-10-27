// ESLint pre skripty webapp (static/js). Kontroluje to CI (.github/workflows/lint.yml); lokálne:
//   cd tester/webapp && npm install --no-save --no-package-lock eslint@9.39.5 @eslint/js@9.39.5 globals@15.15.0
//   npx eslint static/js
//
// Skripty sú klasické <script> z index.html, nie moduly: čo jeden deklaruje navrchu, vidia všetky.
// Tie mená sa preto zbierajú zo všetkých súborov a idú ako globals — `no-undef` potom chytí len
// meno, ktoré nedeklaruje nikto (napr. zmazaná funkcia, ktorú ešte niekto volá).
import js from "@eslint/js";
import globals from "globals";
import * as espree from "espree";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const JS_DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), "static", "js");

function topLevelNames(file) {
  const ast = espree.parse(fs.readFileSync(file, "utf8"), { ecmaVersion: 2022, sourceType: "script" });
  const names = [];
  for (const node of ast.body) {
    if (node.type === "VariableDeclaration") {
      for (const d of node.declarations) if (d.id.type === "Identifier") names.push(d.id.name);
    } else if ((node.type === "FunctionDeclaration" || node.type === "ClassDeclaration") && node.id) {
      names.push(node.id.name);
    }
  }
  return names;
}

const shared = {};
for (const f of fs.readdirSync(JS_DIR).filter((n) => n.endsWith(".js"))) {
  for (const name of topLevelNames(path.join(JS_DIR, f))) shared[name] = "writable";
}

export default [
  js.configs.recommended,
  {
    files: ["static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: { ...globals.browser, ...shared, Plotly: "readonly" },
    },
    rules: {
      // zdieľané mená sú v globals aj deklarované vo svojom súbore — to nie je redeklarácia
      "no-redeclare": ["error", { builtinGlobals: false }],
      // top-level funkcie volajú iné súbory, preto len lokálne premenné
      "no-unused-vars": ["error", { vars: "local", args: "none", caughtErrors: "none" }],
    },
  },
];
