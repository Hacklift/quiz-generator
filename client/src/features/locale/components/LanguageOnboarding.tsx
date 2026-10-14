import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@features/auth/context/authContext";
import { useLocale } from "@features/locale/context/localeContext";
import LanguagePicker from "./LanguagePicker";

export default function LanguageOnboarding() {
  const { user, isLoading } = useAuth();
  const { locale, preferredLocale, setPreferredLocale } = useLocale();
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);
  if (isLoading || !user || user.language_selected || user.preferred_locale)
    return null;
  const save = async (next: string | null) => {
    setBusy(true);
    setError(false);
    try {
      await setPreferredLocale(next);
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="language-onboarding-title"
      className="fixed inset-0 z-[150] overflow-auto bg-black/70 p-6"
    >
      <section className="mx-auto my-12 max-w-xl space-y-4 rounded bg-white p-6 text-gray-900">
        <h1 id="language-onboarding-title" className="text-2xl font-bold">
          {t("language.welcome")}
        </h1>
        <LanguagePicker
          value={preferredLocale ?? locale}
          onChange={(next) => void save(next)}
          disabled={busy}
          allowOrganizationDefault={Boolean(user.onboarding_organization_id)}
        />
        <button
          type="button"
          disabled={busy}
          className="rounded bg-blue-900 px-4 py-2 text-white"
          onClick={() =>
            void save(user.onboarding_organization_id ? null : locale)
          }
        >
          {t("language.continue")}
        </button>
        {error && <p role="alert">{t("language.saveError")}</p>}
      </section>
    </div>
  );
}
