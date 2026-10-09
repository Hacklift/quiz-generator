/**
 * Extract the source catalog and literal message references with TypeScript's
 * parser. Dynamic role/term keys are included through the complete catalog.
 * --check validates migrated namespaces only; it does not claim to detect all
 * untranslated JSX in legacy screens.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const directory = path.join(root, "src/features/locale/messages");
const namespaces = { translation: "", persona: "persona." };
const locales = ["en", "es", "fr"];
const errors = [];
const flatten = (object, prefix = "") =>
  Object.fromEntries(
    Object.entries(object).flatMap(([key, value]) => {
      const id = prefix ? `${prefix}.${key}` : key;
      return typeof value === "string"
        ? [[id, value]]
        : Object.entries(flatten(value, id));
    }),
  );
const placeholders = (value) =>
  [...value.matchAll(/{{\s*([^{}]+?)\s*}}/g)]
    .map((match) => match[1])
    .sort()
    .join("|");
const catalogs = Object.fromEntries(
  Object.entries(namespaces).map(([ns, prefix]) => [
    ns,
    Object.fromEntries(
      locales.map((locale) => [
        locale,
        flatten(
          JSON.parse(
            fs.readFileSync(
              path.join(directory, `${prefix}${locale}.json`),
              "utf8",
            ),
          ),
        ),
      ]),
    ),
  ]),
);
for (const [ns, translations] of Object.entries(catalogs)) {
  for (const locale of locales) {
    for (const [key, source] of Object.entries(translations.en)) {
      const translated = translations[locale][key];
      if (!translated?.trim())
        errors.push(`${locale}:${ns}:${key} is missing or empty`);
      else if (placeholders(source) !== placeholders(translated)) {
        errors.push(`${locale}:${ns}:${key} has different placeholders`);
      }
    }
    for (const key of Object.keys(translations[locale])) {
      if (!(key in translations.en))
        errors.push(`${locale}:${ns}:${key} has no source message`);
    }
  }
}

function* files(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) yield* files(full);
    else if (/\.tsx?$/.test(entry.name)) yield full;
  }
}
const references = {};
const dynamicReferences = [];
for (const file of [
  ...files(path.join(root, "src")),
  ...files(path.join(root, "pages")),
]) {
  const source = ts.createSourceFile(
    file,
    fs.readFileSync(file, "utf8"),
    ts.ScriptTarget.Latest,
    true,
  );
  const translators = new Map();
  const visit = (node, callback) => {
    callback(node);
    ts.forEachChild(node, (child) => visit(child, callback));
  };
  visit(source, (node) => {
    if (
      !ts.isVariableDeclaration(node) ||
      !ts.isObjectBindingPattern(node.name)
    )
      return;
    const call = node.initializer;
    if (
      !call ||
      !ts.isCallExpression(call) ||
      !ts.isIdentifier(call.expression)
    )
      return;
    const hook = call.expression.text;
    if (!["useTranslation", "usePersonaCopy"].includes(hook)) return;
    const namespace =
      hook === "usePersonaCopy"
        ? "persona"
        : call.arguments[0] && ts.isStringLiteral(call.arguments[0])
          ? call.arguments[0].text
          : "translation";
    for (const element of node.name.elements) {
      if (
        (element.propertyName?.getText(source) ??
          element.name.getText(source)) === "t"
      ) {
        translators.set(element.name.getText(source), namespace);
      }
    }
  });
  visit(source, (node) => {
    if (!ts.isCallExpression(node) || !ts.isIdentifier(node.expression)) return;
    const ns = translators.get(node.expression.text);
    if (!ns) return;
    const argument = node.arguments[0];
    if (!argument) return;
    const location = `${path.relative(root, file)}:${source.getLineAndCharacterOfPosition(node.getStart()).line + 1}`;
    if (!ts.isStringLiteral(argument)) {
      dynamicReferences.push({
        namespace: ns,
        expression: argument.getText(source),
        location,
      });
      return;
    }
    const key = argument.text;
    const messages = catalogs[ns]?.en;
    if (
      !messages ||
      (!(key in messages) &&
        !(`${key}_one` in messages && `${key}_other` in messages))
    ) {
      errors.push(`${location}: missing source message ${ns}:${key}`);
    }
    (references[`${ns}:${key}`] ??= []).push(location);
  });
}
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
if (process.argv.includes("--extract")) {
  const messages = Object.entries(catalogs).flatMap(
    ([namespace, translations]) =>
      Object.entries(translations.en).map(([key, source]) => ({
        namespace,
        key,
        source,
        references: references[`${namespace}:${key}`] ?? [],
      })),
  );
  console.log(JSON.stringify({ messages, dynamicReferences }, null, 2));
} else {
  console.log(
    "i18n check passed: en/es/fr catalogs, placeholders, and literal references.",
  );
}
