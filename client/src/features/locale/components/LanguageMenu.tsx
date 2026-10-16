import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocale } from "../context/localeContext";
import LanguagePicker from "./LanguagePicker";

/** Available before registration as well as to independent, signed-in learners. */
export default function LanguageMenu() {
  const { t } = useTranslation();
  const { locale, setPreferredLocale, translationStatus } = useLocale();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  const [open, setOpen] = useState(false);
  return (
    <details
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className="fixed bottom-3 left-3 z-[100] max-w-[calc(100vw-24px)] rounded border bg-white p-2 text-gray-900 shadow-lg"
    >
      <summary className="cursor-pointer px-2 py-1">
        {t("language.settings")} · {locale}
      </summary>
      {open && (
        <div className="max-h-[70vh] w-80 max-w-full overflow-auto p-2">
          <LanguagePicker
            value={locale}
            disabled={busy}
            onChange={async (next) => {
              setBusy(true);
              setError(false);
              try {
                await setPreferredLocale(next);
              } catch {
                setError(true);
              } finally {
                setBusy(false);
              }
            }}
          />
          <p role="status" className="mt-2 text-sm">
            {busy
              ? t("language.saving")
              : translationStatus === "loading"
                ? t("language.loading")
                : translationStatus === "unavailable"
                  ? t("language.unavailable")
                  : null}
          </p>
          {error && <p role="alert">{t("language.saveError")}</p>}
        </div>
      )}
    </details>
  );
}
