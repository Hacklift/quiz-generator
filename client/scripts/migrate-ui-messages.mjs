// Emits reviewable edits; does not write files. Apply the output as a patch.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import ts from "typescript";

const root = process.cwd();
const messages = {};
const changes = {};
const skipped = [];
const keyFor = text => "m" + crypto.createHash("sha256").update(text).digest("hex").slice(0, 16);
const decode = s => s.replace(/&(?:apos|#39);/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&")
  .replace(/&nbsp;/g, " ").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
const textValue = s => decode(s.replace(/\s+/g, " ").trim());
const isText = s => /[a-zA-Z]{2}/.test(s) && !/^(https?:|\/|#|@)/.test(s);
function* files(dir) {
  for (const d of fs.readdirSync(dir, {withFileTypes:true})) {
    const p = path.join(dir, d.name);
    if (d.isDirectory()) yield* files(p);
    else if (/\.tsx$/.test(d.name)) yield p;
  }
}
const attributes = new Set(["placeholder", "title", "alt", "aria-label", "label", "heading", "description", "emptyMessage", "loadingText"]);
for (const file of [...files("src"), ...files("pages")]) {
  if (process.argv[2] && file !== process.argv[2]) continue;
  if (file.includes("features/locale/")) continue;
  const old = fs.readFileSync(file, "utf8");
  if (old.includes('useTranslation("ui")')) continue;
  const ast = ts.createSourceFile(file, old, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const edits = [];
  const owners = new Set();
  function owner(node) {
    for (let p = node.parent; p; p = p.parent) {
      if (!ts.isFunctionDeclaration(p) && !ts.isArrowFunction(p) && !ts.isFunctionExpression(p)) continue;
      const name = p.name?.text || (ts.isVariableDeclaration(p.parent) ? p.parent.name.getText(ast) : "");
      if (/^[A-Z]/.test(name) && p.body) return p;
    }
    return null;
  }
  function add(node, text, kind = "expression", opts = "") {
    if (!isText(text)) return;
    const owning = owner(node);
    if (!owning) { skipped.push({file, line:ast.getLineAndCharacterOfPosition(node.pos).line+1, text}); return; }
    const id = keyFor(text); messages[id] = text;
    let replacement = 'uiText("' + id + '"' + opts + ')';
    if (kind === "jsx" || kind === "attribute") replacement = "{" + replacement + "}";
    edits.push({start:node.getStart(ast), end:node.end, text:replacement});
    owners.add(owning);
  }
  function visit(node) {
    if (ts.isJsxText(node)) {
      const text = textValue(node.text);
      add(node, text, "jsx");
      return;
    }
    if (ts.isJsxAttribute(node) && attributes.has(node.name.text) && node.initializer && ts.isStringLiteral(node.initializer)) {
      add(node.initializer, decode(node.initializer.text), "attribute"); return;
    }
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
      const p = node.parent;
      let jsxValue = false;
      // Literals in conditional JSX expressions are display copy, not CSS or route values.
      let ancestor = p;
      while (ancestor && (ts.isConditionalExpression(ancestor) || ts.isParenthesizedExpression(ancestor) || ts.isBinaryExpression(ancestor))) ancestor = ancestor.parent;
      if (ancestor && ts.isJsxExpression(ancestor) && !ts.isJsxAttribute(ancestor.parent)) jsxValue = true;
      const callName = ts.isCallExpression(p) ? p.expression.getText(ast) : "";
      const displayCall = /^(toast\.(success|error|loading)|setError|setSaveError|setErrorMessage)$/.test(callName);
      if (jsxValue || displayCall) { add(node, node.text); return; }
    }
    if (ts.isTemplateExpression(node) && ts.isJsxExpression(node.parent) && !ts.isJsxAttribute(node.parent.parent)) {
      let text = node.head.text; const vars=[];
      for (const [i, span] of node.templateSpans.entries()) {
        text += "{{value" + i + "}}" + span.literal.text;
        vars.push("value" + i + ": " + span.expression.getText(ast));
      }
      add(node, text, "expression", ", { " + vars.join(", ") + " }"); return;
    }
    ts.forEachChild(node, visit);
  }
  visit(ast);
  if (!edits.length) continue;
  for (const fn of owners) {
    if (ts.isBlock(fn.body)) {
      edits.push({start:fn.body.getStart(ast)+1, end:fn.body.getStart(ast)+1, text:'\n  const { t: uiText } = useTranslation("ui");\n'});
    } else {
      edits.push({start:fn.body.getStart(ast), end:fn.body.getStart(ast), text:'{ const { t: uiText } = useTranslation("ui"); return '});
      edits.push({start:fn.body.end, end:fn.body.end, text:'; }'});
    }
  }
  let content = old;
  for (const edit of edits.sort((a,b)=>b.start-a.start)) content = content.slice(0,edit.start)+edit.text+content.slice(edit.end);
  if (!/import\s*\{[^}]*\buseTranslation\b[^}]*\}\s*from\s*["']react-i18next["']/.test(content)) {
    // Imports may legally follow the use-client directive.
    const pos = content.startsWith('"use client";') ? '"use client";'.length : 0;
    content = content.slice(0,pos)+'\nimport { useTranslation } from "react-i18next";\n'+content.slice(pos);
  }
  changes[file] = {old, content};
}
const only = process.argv[2];
console.log(JSON.stringify(only ? changes[only] : {files:Object.keys(changes),messages,skipped}));
