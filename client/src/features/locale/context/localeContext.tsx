import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import { I18nextProvider } from "react-i18next";
import { useAuth } from "@features/auth/context/authContext";
import { updateLocale } from "@features/auth/api/authApi";
import {
  browserLocale,
  DEFAULT_LOCALE,
  type SupportedLocale,
} from "@shared/config/locale";
import { createLocaleI18n } from "@features/locale/i18n";

interface LocaleContextValue {
  locale: SupportedLocale;
  preferredLocale: SupportedLocale | null;
  setPreferredLocale: (locale: SupportedLocale | null) => Promise<void>;
}

const LocaleContext = createContext<LocaleContextValue | undefined>(undefined);

export function LocaleProvider({ children }: { children: ReactNode }) {
  const { user, refreshUser } = useAuth();
  const [i18n] = useState(createLocaleI18n);
  const [locale, setLocale] = useState<SupportedLocale>(DEFAULT_LOCALE);

  useEffect(() => {
    const nextLocale = user
      ? (user.preferred_locale ?? user.effective_locale ?? DEFAULT_LOCALE)
      : browserLocale();
    setLocale(nextLocale);
    void i18n.changeLanguage(nextLocale);
  }, [i18n, user?.id, user?.preferred_locale, user?.effective_locale]);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = "ltr";
  }, [locale]);

  const setPreferredLocale = useCallback(
    async (preferredLocale: SupportedLocale | null) => {
      if (!user) throw new Error("Sign in to update your language preference.");

      // A cleared preference must be resolved by the server, since it may
      // inherit an organization locale. Publish changes after persistence.
      await updateLocale({ preferred_locale: preferredLocale });
      await refreshUser();
    },
    [refreshUser, user],
  );

  const value = useMemo(
    () => ({
      locale,
      preferredLocale: user?.preferred_locale ?? null,
      setPreferredLocale,
    }),
    [locale, setPreferredLocale, user?.preferred_locale],
  );

  return (
    <I18nextProvider i18n={i18n}>
      <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
    </I18nextProvider>
  );
}

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  return (
    context ?? {
      locale: DEFAULT_LOCALE,
      preferredLocale: null,
      setPreferredLocale: async () => {
        throw new Error("Language changes require LocaleProvider");
      },
    }
  );
}
