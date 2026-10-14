import type { i18n } from "i18next";
import { API_BASE_URL, api } from "@shared/api/http";

type Catalog = {
  locale: string;
  namespace: string;
  version: string;
  messages: Record<string, string>;
  missing: string[];
};
const namespaces = ["translation", "persona", "ui"];
const bundled = new Set(["en", "es", "fr"]);

function install(instance: i18n, catalog: Catalog) {
  // addResources interprets dotted keys; addResourceBundle would not override
  // nested bundled persona/terminology messages correctly.
  instance.addResources(catalog.locale, catalog.namespace, catalog.messages);
}

export async function loadLanguageCatalogs(
  instance: i18n,
  locale: string,
  signedIn: boolean,
  signal: AbortSignal,
  onStatus: (status: "loading" | "ready" | "unavailable") => void,
) {
  if (locale === "en") {
    onStatus("ready");
    return;
  }
  onStatus("loading");
  let unavailable = false;
  for (const namespace of namespaces) {
    if (signal.aborted) return;
    const cacheKey = "quizwerk.catalog." + locale + "." + namespace;
    let cached: Catalog | undefined;
    try {
      const value = localStorage.getItem(cacheKey);
      if (value) {
        const parsed = JSON.parse(value);
        if (
          parsed.locale === locale &&
          parsed.namespace === namespace &&
          typeof parsed.version === "string" &&
          parsed.messages &&
          Object.values(parsed.messages).every(
            (message) => typeof message === "string",
          ) &&
          Array.isArray(parsed.missing)
        ) {
          cached = parsed;
          install(instance, parsed);
        }
      }
    } catch {
      /* Storage can be blocked or full. Bundled catalogs still work. */
    }
    try {
      const response = await fetch(
        API_BASE_URL + "/api/i18n/catalogs/" + locale + "/" + namespace,
        { signal },
      );
      if (!response.ok) throw new Error("Catalog unavailable");
      let catalog: Catalog = await response.json();
      if (catalog.locale !== locale || catalog.namespace !== namespace)
        throw new Error("Wrong catalog");
      if (signal.aborted) return;
      if (cached?.version !== catalog.version && !bundled.has(locale)) {
        instance.removeResourceBundle(locale, namespace);
      }
      const publish = () => {
        if (signal.aborted) return;
        install(instance, catalog);
        try {
          localStorage.setItem(cacheKey, JSON.stringify(catalog));
        } catch {}
      };
      publish();
      if (!signedIn && catalog.missing.length) {
        unavailable = true;
        continue;
      }
      while (signedIn && catalog.missing.length && !signal.aborted) {
        const next = await api.post<Catalog>(
          "/api/i18n/catalogs/" + locale + "/" + namespace,
          { keys: catalog.missing.slice(0, 64) },
          { signal },
        );
        if (
          next.data.locale !== locale ||
          next.data.namespace !== namespace ||
          next.data.missing.length >= catalog.missing.length
        )
          throw new Error("No translation progress");
        catalog = next.data;
        publish();
      }
    } catch {
      if (!bundled.has(locale) && (!cached || cached.missing.length))
        unavailable = true;
    }
  }
  if (!signal.aborted) onStatus(unavailable ? "unavailable" : "ready");
}
