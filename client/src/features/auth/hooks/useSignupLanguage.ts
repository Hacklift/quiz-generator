import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { api } from "@shared/api/http";
import { isSupportedLocale } from "@shared/config/locale";
import { useLocale } from "@features/locale/context/localeContext";

interface InvitationPreview {
  organization_id: string;
  name: string;
  default_locale: string;
}

function guestPreference(): string | null {
  try {
    const saved = localStorage.getItem("quizwerk.guestLocale");
    if (isSupportedLocale(saved)) return saved;
  } catch {}
  return null;
}

export function useSignupLanguage(isOpen: boolean) {
  const router = useRouter();
  const { previewGuestLocale } = useLocale();
  const [preference, setPreference] = useState<string | null>(null);
  const [invitation, setInvitation] = useState<InvitationPreview | null>(null);
  const [invitationToken, setInvitationToken] = useState("");
  const [checkingInvitation, setCheckingInvitation] = useState(false);
  const [invitationError, setInvitationError] = useState(false);
  const queryToken =
    typeof router.query?.organization_invite === "string"
      ? router.query.organization_invite
      : "";
  const routerReady = router.isReady !== false;

  useEffect(() => {
    if (!isOpen || !routerReady) return;
    const controller = new AbortController();
    const token =
      queryToken ||
      new URLSearchParams(window.location.hash.slice(1)).get(
        "organization_invite",
      ) ||
      "";
    const initial = token ? null : guestPreference();
    setPreference(initial);
    setInvitationToken(token);
    setInvitation(null);
    setInvitationError(false);
    setCheckingInvitation(Boolean(token));
    previewGuestLocale?.(initial || "en");
    if (token) {
      void api
        .post<InvitationPreview>(
          "/api/organizations/onboarding/preview",
          { token },
          { signal: controller.signal },
        )
        .then(({ data }) => {
          if (controller.signal.aborted) return;
          if (
            !isSupportedLocale(data.default_locale) ||
            typeof data.name !== "string"
          )
            throw new Error("Invalid invitation preview");
          setInvitation(data);
          previewGuestLocale?.(data.default_locale);
        })
        .catch(() => {
          if (!controller.signal.aborted) setInvitationError(true);
        })
        .finally(() => {
          if (!controller.signal.aborted) setCheckingInvitation(false);
        });
    }
    return () => {
      controller.abort();
      previewGuestLocale?.(guestPreference() || "en");
    };
  }, [isOpen, routerReady, queryToken, router.asPath, previewGuestLocale]);

  const chooseLanguage = (next: string | null) => {
    setPreference(next);
    previewGuestLocale?.(next || invitation?.default_locale || "en");
  };

  return {
    preference,
    chooseLanguage,
    invitation,
    invitationToken,
    checkingInvitation: checkingInvitation || !routerReady,
    invitationError,
  };
}
