import { useId, useMemo, useState } from "react";
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
}: {
  value: SupportedLocale | null;
  onChange: (locale: SupportedLocale | null) => void;
  disabled?: boolean;
  allowOrganizationDefault?: boolean;
}) {
  const { t, i18n } = useTranslation();
  const id = useId();
  const [query, setQuery] = useState("");
  const names = useMemo(() => {
    let display: Intl.DisplayNames | undefined;
    try {
      display = new Intl.DisplayNames([i18n.language || "en"], {
        type: "language",
      });
    } catch {}
    return LANGUAGES.map(({ code, name }) => {
      let localized = name;
      let native = LOCALE_DISPLAY_NAMES[code];
      try {
        localized = display?.of(code) || name;
        native =
          new Intl.DisplayNames([code], { type: "language" }).of(code) ||
          native;
      } catch {}
      return {
        code,
        name,
        label: Array.from(new Set([native, localized, name])).join(" · "),
      };
    });
  }, [i18n.language]);
  const matches = names.filter(({ code, name, label }) =>
    fold(code + " " + name + " " + label).includes(fold(query)),
  );
  const selected = value || "en";
  const visible = matches.some((x) => x.code === selected)
    ? matches
    : [...names.filter((x) => x.code === selected), ...matches];
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
        onChange={(event) => setQuery(event.target.value)}
        disabled={disabled}
        placeholder={t("language.searchPlaceholder")}
        className="w-full rounded border border-gray-300 bg-white p-2 text-gray-900"
      />
      <label className="block font-medium" htmlFor={id}>
        {t("language.settings")}
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
      {matches.length === 0 && <p role="status">{t("language.noMatches")}</p>}
      <p className="text-sm text-gray-600">{t("language.coverage")}</p>
    </div>
  );
}
