import { useEffect, useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  LANGUAGES,
  LOCALE_DISPLAY_NAMES,
  type SupportedLocale,
} from "@shared/config/locale";

const fold = (value: string) =>
  value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

/** Search stays visible; a native select retains keyboard and screen-reader support. */
export default function LanguagePicker({
  value,
  onChange,
  disabled = false,
  allowOrganizationDefault = false,
  label,
}: {
  value: SupportedLocale | null;
  onChange: (locale: SupportedLocale | null) => void;
  disabled?: boolean;
  allowOrganizationDefault?: boolean;
  label?: string;
}) {
  const { t, i18n } = useTranslation();
  const id = useId();
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(100);
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  const names = useMemo(() => {
    // Node and browsers may ship different Intl/ICU language data. Keep SSR
    // and the first browser render identical; enrich labels only after mount.
    let display: Intl.DisplayNames | undefined;
    if (hydrated) {
      try {
        display = new Intl.DisplayNames([i18n.language || "en"], {
          type: "language",
          fallback: "none",
        });
      } catch {}
    }
    return LANGUAGES.map(({ code, name }) => {
      let localized = name;
      let native = LOCALE_DISPLAY_NAMES[code];
      try {
        localized = display?.of(code) || name;
        if (hydrated && code.length === 2) {
          native =
            new Intl.DisplayNames([code], {
              type: "language",
              fallback: "none",
            }).of(code) || native;
        }
      } catch {}
      return {
        code,
        name,
        label: Array.from(new Set([native, localized, name])).join(" · "),
      };
    });
  }, [hydrated, i18n.language]);
  const matches = names.filter(({ code, name, label }) =>
    fold(code + " " + name + " " + label).includes(fold(query)),
  );
  const selected = value || "en";
  // Keep every registry entry searchable without mounting thousands of DOM
  // options on every page. More results remain available through pagination.
  const page = matches.slice(0, limit);
  const visible = page.some((x) => x.code === selected)
    ? page
    : [...names.filter((x) => x.code === selected), ...page];
  return (
    <div className="space-y-2">
      <label className="block font-medium" htmlFor={id + "-search"}>
        {t("language.search")}
      </label>
      <input
        id={id + "-search"}
        type="search"
        autoComplete="off"
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setLimit(100);
        }}
        disabled={disabled}
        placeholder={t("language.searchPlaceholder")}
        className="w-full rounded border border-gray-300 bg-white p-2 text-gray-900"
      />
      <label className="block font-medium" htmlFor={id}>
        {label || t("language.settings")}
      </label>
      <select
        id={id}
        value={
          value === null && allowOrganizationDefault ? "inherit" : selected
        }
        disabled={disabled}
        size={6}
        onChange={(event) =>
          onChange(event.target.value === "inherit" ? null : event.target.value)
        }
        className="w-full rounded border border-gray-300 bg-white p-2 text-gray-900"
      >
        {allowOrganizationDefault && (
          <option value="inherit">
            {t("language.useOrganizationDefault")}
          </option>
        )}
        {visible.map(({ code, label }) => (
          <option key={code} value={code}>
            {label} ({code})
          </option>
        ))}
      </select>
      {matches.length > limit && (
        <button
          type="button"
          disabled={disabled}
          className="text-sm underline"
          onClick={() => setLimit((previous) => previous + 100)}
        >
          {t("language.more")}
        </button>
      )}
      {matches.length === 0 && <p role="status">{t("language.noMatches")}</p>}
      <p className="text-sm text-gray-600">{t("language.coverage")}</p>
    </div>
  );
}
