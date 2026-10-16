import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import { Settings } from "lucide-react";
import { useAuth } from "@features/auth/context/authContext";
import {
  updateProfile,
  requestEmailChange,
  verifyEmailChange,
  deleteAccount,
} from "@features/auth/api/authApi";
import {
  SubscriptionSummary,
  createPortalSession,
  getBillingErrorMessage,
  getSubscriptionSummary,
} from "@features/profile/api/billingApi";
import NavBar from "@features/quiz/components/NavBar";
import Footer from "@features/quiz/components/Footer";
import RequireAuth from "@features/auth/components/RequireAuth";
import PersonaPicker from "@features/persona/components/PersonaPicker";
import { usePersona } from "@features/persona/context/personaContext";
import LanguagePicker from "@features/locale/components/LanguagePicker";
import { useLocale } from "@features/locale/context/localeContext";
import {
  LOCALE_DISPLAY_NAMES,
  SUPPORTED_LOCALES,
  type SupportedLocale,
} from "@shared/config/locale";
import { useTranslation } from "react-i18next";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";

export default function ProfilePage() {
  const { t: uiText, i18n } = useTranslation("ui");

  const { user, isLoading, logout, refreshUser } = useAuth();
  const { persona, definition, categoryDefinition } = usePersona();
  const { preferredLocale, setPreferredLocale } = useLocale();
  const { t } = useTranslation();
  const { t: personaText } = usePersonaCopy();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [emailOtp, setEmailOtp] = useState("");
  const [emailChangePending, setEmailChangePending] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [publicProfile, setPublicProfile] = useState(false);
  const [activeSettingSection, setActiveSettingSection] = useState<
    "account" | "billing" | "language" | "profile" | "persona" | null
  >(null);
  const [paymentNotice, setPaymentNotice] = useState<{
    type: "cancelled" | "success";
    message: string;
  } | null>(null);
  const [isOpeningPortal, setIsOpeningPortal] = useState(false);
  const [isSavingLocale, setIsSavingLocale] = useState(false);
  const [billingSummary, setBillingSummary] =
    useState<SubscriptionSummary | null>(null);

  const [formData, setFormData] = useState({
    full_name: "",
    bio: "",
    location: "",
    website: "",
    avatar_color: "#143E6F",
  });

  useEffect(() => {
    if (user) {
      setFormData({
        full_name: user.full_name || "",
        bio: user.bio || "",
        location: user.location || "",
        website: user.website || "",
        avatar_color: user.avatar_color || "#143E6F",
      });
    }
  }, [user]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const storedPublicProfile = localStorage.getItem("public_profile_enabled");
    if (storedPublicProfile) {
      setPublicProfile(storedPublicProfile === "true");
    }
  }, []);

  useEffect(() => {
    if (!user) {
      setBillingSummary(null);
      return;
    }

    setBillingSummary({
      subscription_plan: user.subscription_plan || "free",
      subscription_status: user.subscription_status || "inactive",
      stripe_customer_id: user.stripe_customer_id,
      stripe_subscription_id: user.stripe_subscription_id,
      current_period_end: user.current_period_end,
    });
  }, [user]);

  useEffect(() => {
    if (!router.isReady) {
      return;
    }

    const paymentState = Array.isArray(router.query.payment)
      ? router.query.payment[0]
      : router.query.payment;

    if (paymentState === "success") {
      setPaymentNotice({
        type: "success",
        message:
          "Payment completed. Your subscription status has been refreshed.",
      });

      void (async () => {
        try {
          let latestSummary: SubscriptionSummary | null = null;

          for (let attempt = 0; attempt < 4; attempt += 1) {
            latestSummary = await getSubscriptionSummary();
            setBillingSummary(latestSummary);

            if (
              latestSummary.current_period_end ||
              latestSummary.subscription_status === "active"
            ) {
              break;
            }

            await new Promise((resolve) => setTimeout(resolve, 1500));
          }

          await refreshUser();
        } catch (error: any) {
          toast.error(
            getBillingErrorMessage(
              error,
              "Payment succeeded, but the profile refresh failed.",
            ),
          );
        } finally {
          void router.replace("/profile", undefined, { shallow: true });
        }
      })();
      return;
    }

    if (paymentState === "cancelled") {
      setPaymentNotice({
        type: "cancelled",
        message: "Checkout was cancelled. No changes were made to your plan.",
      });
      void router.replace("/profile", undefined, { shallow: true });
    }
  }, [refreshUser, router, router.isReady, router.query.payment]);

  useEffect(() => {
    if (!user?.stripe_customer_id || user.current_period_end) {
      return;
    }

    void getSubscriptionSummary()
      .then((summary) => {
        setBillingSummary(summary);
      })
      .catch(() => {
        // Keep the current profile snapshot if reconciliation fails.
      });
  }, [user?.current_period_end, user?.stripe_customer_id]);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      setIsLoggingOut(false);
      setShowLogoutConfirm(false);
    }
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setSaveError("");
  };

  const handleSaveProfile = async () => {
    if (user && user.is_verified === false) {
      toast.error(uiText("m10cf11c897a08692"));
      return;
    }

    setIsSaving(true);
    setSaveError("");
    setSaveSuccess(false);

    try {
      await updateProfile(formData);
      setSaveSuccess(true);
      setIsEditing(false);

      if (refreshUser) {
        await refreshUser();
      }
      if (typeof window !== "undefined") {
        localStorage.setItem(
          "public_profile_enabled",
          publicProfile ? "true" : "false",
        );
      }

      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error: any) {
      setSaveError(error.message || uiText("meeb7276dab30a337"));
    } finally {
      setIsSaving(false);
    }
  };

  const handleRequestPasswordReset = () => {
    router.push("/auth/request-reset-password");
  };

  const handleUpdateEmail = async () => {
    if (!newEmail.trim()) {
      toast.error(uiText("md0cb54952d33cbfc"));
      return;
    }
    try {
      await requestEmailChange(newEmail.trim());
      setEmailChangePending(true);
      toast.success(uiText("ma4cfdc73bfcb2671"));
    } catch (error: any) {
      toast.error(error?.message || uiText("mb780699d95333157"));
    }
  };

  const handleVerifyEmailChange = async () => {
    if (!emailOtp.trim()) {
      toast.error(uiText("medadbd5aa4f49cc8"));
      return;
    }
    try {
      await verifyEmailChange(emailOtp.trim());
      setEmailChangePending(false);
      setEmailOtp("");
      setNewEmail("");
      await refreshUser();
      toast.success(uiText("mcad80028698178d3"));
    } catch (error: any) {
      toast.error(error?.message || uiText("m8062a0d1f9c034d9"));
    }
  };

  const handleDeleteAccount = async () => {
    try {
      await deleteAccount();
      setShowDeleteConfirm(false);
      await logout();
    } catch (error: any) {
      toast.error(error?.message || uiText("m83326cc97ff9fac2"));
    }
  };

  const handleLocaleChange = async (locale: SupportedLocale | null) => {
    setIsSavingLocale(true);
    try {
      await setPreferredLocale(locale);
      toast.success(t("language.saved"));
    } catch (error: any) {
      toast.error(error?.message || t("language.saveError"));
    } finally {
      setIsSavingLocale(false);
    }
  };

  const handleManageSubscription = async () => {
    try {
      setIsOpeningPortal(true);
      const { portal_url } = await createPortalSession();
      window.location.assign(portal_url);
    } catch (error: any) {
      toast.error(
        getBillingErrorMessage(error, "Unable to open the billing portal."),
      );
    } finally {
      setIsOpeningPortal(false);
    }
  };

  const handleCancelEdit = () => {
    if (user) {
      setFormData({
        full_name: user.full_name || "",
        bio: user.bio || "",
        location: user.location || "",
        website: user.website || "",
        avatar_color: user.avatar_color || "#143E6F",
      });
    }
    setIsEditing(false);
    setSaveError("");
  };

  const avatarColors = [
    "#143E6F",
    "#2563eb",
    "#7c3aed",
    "#db2777",
    "#dc2626",
    "#ea580c",
    "#ca8a04",
    "#16a34a",
    "#0891b2",
    "#6366f1",
  ];

  const billingPlan =
    billingSummary?.subscription_plan || user?.subscription_plan || "free";
  const billingStatus =
    billingSummary?.subscription_status ||
    user?.subscription_status ||
    "inactive";
  const billingRenewalDate =
    billingSummary?.current_period_end || user?.current_period_end || null;
  const hasBillingPortalAccess = Boolean(
    billingSummary?.stripe_customer_id || user?.stripe_customer_id,
  );

  const formatPlanLabel = (plan?: string) => {
    if (!plan || plan === "free") {
      return "Free";
    }
    return plan.charAt(0).toUpperCase() + plan.slice(1);
  };

  const formatStatusLabel = (status?: string) => {
    if (!status || status === "inactive") {
      return "Inactive";
    }
    return status
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  };

  const subscriptionStatusClassName =
    billingStatus === "active"
      ? "bg-green-100 text-green-800"
      : billingStatus === "past_due"
        ? "bg-amber-100 text-amber-800"
        : "bg-gray-100 text-gray-700";
  const personaLabel =
    categoryDefinition && definition
      ? `${categoryDefinition.label} · ${definition.label}`
      : personaText("profile.unset");

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#143E6F]"></div>
          <p className="mt-4 text-gray-600">{uiText("m47d2a515ef2f05b8")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <NavBar />

      <RequireAuth
        title={uiText("m991bfa015514f9d5")}
        description={uiText("m0bbb194809df9769")}
      >
        <main className="flex-grow mx-auto px-4 py-8 w-full max-w-6xl">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-3xl font-bold text-[#143E6F]">
              {uiText("m991bfa015514f9d5")}
            </h1>
            <button
              onClick={() => {
                setIsSettingsOpen((prev) => !prev);
                setActiveSettingSection(null);
              }}
              className="p-2 rounded-full border border-gray-200 text-[#143E6F] hover:bg-gray-50 transition-colors"
              aria-label={uiText("mca381c1e76e681b6")}
            >
              <Settings size={20} />
            </button>
          </div>

          {saveSuccess && (
            <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 flex items-center">
              <svg
                className="w-5 h-5 text-green-600 mr-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="text-green-800">
                {uiText("m5d76b99b7f954c20")}
              </span>
            </div>
          )}

          {saveError && (
            <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-center">
              <svg
                className="w-5 h-5 text-red-600 mr-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
              <span className="text-red-800">{saveError}</span>
            </div>
          )}

          {paymentNotice && (
            <div
              className={`mb-6 rounded-lg border p-4 ${
                paymentNotice.type === "success"
                  ? "border-green-200 bg-green-50 text-green-800"
                  : "border-amber-200 bg-amber-50 text-amber-800"
              }`}
            >
              {paymentNotice.message}
            </div>
          )}

          <div className="bg-white rounded-2xl shadow-sm p-8 mb-6 max-w-3xl mx-auto w-full">
            <div className="flex items-start mb-6">
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center text-white text-3xl font-bold flex-shrink-0"
                style={{ backgroundColor: formData.avatar_color }}
              >
                {user?.username?.charAt(0).toUpperCase() || "U"}
              </div>
              <div className="ml-6 flex-grow">
                {isEditing ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {uiText("m8e00cdf71fa7cc76")}
                      </label>
                      <input
                        type="text"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        placeholder={uiText("mb3627016e7e783ec")}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {uiText("m7c73323031d48c70")}
                      </label>
                      <div className="flex gap-2 flex-wrap">
                        {avatarColors.map((color) => (
                          <button
                            key={color}
                            type="button"
                            onClick={() =>
                              setFormData((prev) => ({
                                ...prev,
                                avatar_color: color,
                              }))
                            }
                            className={`w-10 h-10 rounded-full transition-transform ${
                              formData.avatar_color === color
                                ? "ring-2 ring-offset-2 ring-[#143E6F] scale-110"
                                : "hover:scale-105"
                            }`}
                            style={{ backgroundColor: color }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div>
                    <h2 className="text-2xl font-semibold text-gray-900">
                      {formData.full_name ||
                        user?.username ||
                        uiText("mb512d97e7cbf97c2")}
                    </h2>
                    <p className="text-gray-500 mt-1">
                      @{user?.username || uiText("m04f8996da763b7a9")}
                    </p>
                    <p className="text-gray-600 mt-2">
                      {user?.email || uiText("mc7e5603e095c22e4")}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="border-t pt-6 mb-6">
              {isEditing ? (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {uiText("m3933b1802161254f")}
                  </label>
                  <textarea
                    name="bio"
                    value={formData.bio}
                    onChange={handleInputChange}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                    placeholder={uiText("m697f10251d5bd2ed")}
                    maxLength={500}
                  />
                  <p className="text-sm text-gray-500 mt-1">
                    {formData.bio.length}/500 characters
                  </p>
                </div>
              ) : (
                formData.bio && (
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {uiText("m3933b1802161254f")}
                    </h3>
                    <p className="text-gray-700">{formData.bio}</p>
                  </div>
                )
              )}
            </div>

            <div className="border-t pt-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                {isEditing
                  ? uiText("m9fd84fecd300b57c")
                  : uiText("m1cb0ba125f84c982")}
              </h3>
              <div className="space-y-4">
                {isEditing ? (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {uiText("m15b61974b2707a7b")}
                      </label>
                      <input
                        type="text"
                        name="location"
                        value={formData.location}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        placeholder={uiText("ma7bc8816f26258d2")}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {uiText("mb5a229ac8becc603")}
                      </label>
                      <input
                        type="url"
                        name="website"
                        value={formData.website}
                        onChange={handleInputChange}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        placeholder="https://yourwebsite.com"
                      />
                    </div>
                  </>
                ) : (
                  <>
                    {formData.location && (
                      <div className="flex items-center">
                        <svg
                          className="w-5 h-5 text-gray-400 mr-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                          />
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                          />
                        </svg>
                        <span className="text-gray-700">
                          {formData.location}
                        </span>
                      </div>
                    )}
                    {formData.website && (
                      <div className="flex items-center">
                        <svg
                          className="w-5 h-5 text-gray-400 mr-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
                          />
                        </svg>
                        <a
                          href={formData.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#143E6F] hover:underline"
                        >
                          {formData.website}
                        </a>
                      </div>
                    )}
                  </>
                )}

                <div className="flex justify-between items-center py-3 border-t">
                  <span className="text-gray-600">
                    {uiText("me3b89e9d33f88e52")}
                  </span>
                  <span className="font-medium text-gray-900">
                    {user?.username || "N/A"}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-t">
                  <span className="text-gray-600">
                    {uiText("m969ccbd3cf6300ec")}
                  </span>
                  <span className="font-medium text-gray-900">
                    {user?.email || "N/A"}
                  </span>
                </div>
                <div className="flex justify-between items-center gap-4 py-3 border-t">
                  <span className="text-gray-600">
                    {uiText("m31bdeef94e7d9a9c")}
                  </span>
                  <span className="text-right font-medium text-gray-900">
                    {personaLabel}
                  </span>
                </div>
                <div className="flex justify-between items-center py-3 border-t">
                  <span className="text-gray-600">
                    {uiText("mdafb01abaf3dd0c7")}
                  </span>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                    {uiText("m92340695899bd2d8")}
                  </span>
                </div>
                <div className="border-t pt-4">
                  <div className="rounded-2xl border border-[#143E6F]/10 bg-[#f8fbff] p-4">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#143E6F]/70">
                          {uiText("m3ac8bbca9a74cfbd")}
                        </p>
                        <h4 className="mt-2 text-lg font-semibold text-[#102347]">
                          {uiText("mb1a74beb41988ef5", {
                            value0: formatPlanLabel(billingPlan),
                          })}
                        </h4>
                        <div className="mt-3">
                          <span
                            className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${subscriptionStatusClassName}`}
                          >
                            {uiText("values." + billingStatus, {
                              ns: "translation",
                              defaultValue: formatStatusLabel(billingStatus),
                            })}
                          </span>
                        </div>
                        <p className="mt-3 text-sm text-gray-600">
                          {billingRenewalDate
                            ? uiText("mdad47b1ee9673d16", {
                                value0: new Date(
                                  billingRenewalDate,
                                ).toLocaleDateString(i18n.language),
                              })
                            : billingPlan === "free"
                              ? uiText("m1d6022df68d719ff")
                              : uiText("m29835dc37c881570")}
                        </p>
                      </div>
                      <div className="flex flex-col sm:flex-row gap-2">
                        {hasBillingPortalAccess ? (
                          <button
                            onClick={handleManageSubscription}
                            disabled={isOpeningPortal}
                            className="rounded-lg bg-[#143E6F] px-4 py-2 text-sm font-medium text-white hover:bg-[#0f2f54] disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {isOpeningPortal
                              ? uiText("maa987d702e9696af")
                              : uiText("m9041c6aa2c3d4670")}
                          </button>
                        ) : (
                          <button
                            onClick={() => router.push("/#pricing")}
                            className="rounded-lg bg-[#143E6F] px-4 py-2 text-sm font-medium text-white hover:bg-[#0f2f54]"
                          >
                            {uiText("ma72e2bd3e148c05e")}
                          </button>
                        )}
                        <button
                          onClick={() => router.push("/billing_history")}
                          className="rounded-lg border border-[#143E6F]/20 px-4 py-2 text-sm font-medium text-[#143E6F] hover:bg-[#143E6F]/5"
                        >
                          {uiText("m9aa99a0fb494e1a8")}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {isEditing && (
              <div className="border-t pt-6 mt-6 flex gap-3">
                <button
                  onClick={handleCancelEdit}
                  disabled={isSaving}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {uiText("m19766ed6ccb2f4a3")}
                </button>
                <button
                  onClick={handleSaveProfile}
                  disabled={isSaving}
                  className="flex-1 bg-[#143E6F] text-white py-2.5 rounded-lg font-medium hover:bg-[#0f2f54] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isSaving
                    ? uiText("mdc85af8f2b1d0d67")
                    : uiText("m35322b5bb5a218a1")}
                </button>
              </div>
            )}
          </div>

          {isSettingsOpen && (
            <div className="bg-white rounded-2xl shadow-sm p-8 max-w-4xl mx-auto w-full space-y-8">
              <div>
                <h3 className="text-xl font-semibold text-gray-900">
                  {uiText("m74a883a037bc227f")}
                </h3>
                <p className="text-sm text-gray-500">
                  {uiText("m4e62cb99b2d7421c")}
                </p>
              </div>

              <div className="space-y-4">
                <div className="border border-[#143E6F]/20 rounded-xl">
                  <button
                    onClick={() =>
                      setActiveSettingSection((prev) =>
                        prev === "billing" ? null : "billing",
                      )
                    }
                    className="w-full px-5 py-4 flex items-center justify-between text-left"
                  >
                    <h4 className="text-lg font-semibold text-[#143E6F]">
                      {uiText("m3ac8bbca9a74cfbd")}
                    </h4>
                    <span className="text-[#143E6F]">
                      {activeSettingSection === "billing" ? "-" : "+"}
                    </span>
                  </button>
                  {activeSettingSection === "billing" && (
                    <div className="border-t border-[#143E6F]/10 p-5 space-y-4">
                      <div className="rounded-xl border border-[#143E6F]/10 bg-[#f8fbff] p-4">
                        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                          <div>
                            <p className="text-sm text-gray-500">
                              {uiText("m37ca715f53b6bb83")}
                            </p>
                            <h5 className="mt-1 text-xl font-semibold text-[#102347]">
                              {formatPlanLabel(billingPlan)}
                            </h5>
                            <p className="mt-2 text-sm text-gray-600">
                              {uiText("md617370d57781737", {
                                value0: formatStatusLabel(billingStatus),
                              })}
                            </p>
                            {billingRenewalDate ? (
                              <p className="mt-1 text-sm text-gray-600">
                                {uiText("mdbafd6547ce2790a", {
                                  value0: new Date(
                                    billingRenewalDate,
                                  ).toLocaleDateString(i18n.language),
                                })}
                              </p>
                            ) : null}
                          </div>
                          <span
                            className={`inline-flex self-start rounded-full px-3 py-1 text-sm font-medium ${subscriptionStatusClassName}`}
                          >
                            {uiText("values." + billingStatus, {
                              ns: "translation",
                              defaultValue: formatStatusLabel(billingStatus),
                            })}
                          </span>
                        </div>
                      </div>

                      <div className="grid gap-3 sm:grid-cols-2">
                        {hasBillingPortalAccess ? (
                          <button
                            onClick={handleManageSubscription}
                            disabled={isOpeningPortal}
                            className="rounded-lg bg-[#143E6F] px-4 py-3 text-left text-white hover:bg-[#0f2f54] disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <p className="font-medium">
                              {isOpeningPortal
                                ? uiText("maa987d702e9696af")
                                : uiText("m9041c6aa2c3d4670")}
                            </p>
                            <p className="mt-1 text-sm text-white/80">
                              {uiText("m1d382a8ab4e5c436")}
                            </p>
                          </button>
                        ) : (
                          <button
                            onClick={() => router.push("/#pricing")}
                            className="rounded-lg bg-[#143E6F] px-4 py-3 text-left text-white hover:bg-[#0f2f54]"
                          >
                            <p className="font-medium">
                              {uiText("m39b7ec1e84022198")}
                            </p>
                            <p className="mt-1 text-sm text-white/80">
                              {uiText("m77f18dd9902e47cf")}
                            </p>
                          </button>
                        )}

                        <button
                          onClick={() => router.push("/billing_history")}
                          className="rounded-lg border border-gray-200 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                        >
                          <p className="font-medium text-gray-900">
                            {uiText("m9aa99a0fb494e1a8")}
                          </p>
                          <p className="mt-1 text-sm text-gray-500">
                            {uiText("m4d0ecb2353213fad")}
                          </p>
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="border border-[#143E6F]/20 rounded-xl">
                  <button
                    onClick={() =>
                      setActiveSettingSection((prev) =>
                        prev === "persona" ? null : "persona",
                      )
                    }
                    className="w-full px-5 py-4 flex items-center justify-between text-left"
                  >
                    <div>
                      <h4 className="text-lg font-semibold text-[#143E6F]">
                        {personaText("profile.title")}
                      </h4>
                      <p className="mt-1 text-sm text-gray-500">
                        {personaText("profile.current", {
                          persona: personaLabel,
                        })}
                      </p>
                    </div>
                    <span className="text-[#143E6F]">
                      {activeSettingSection === "persona" ? "-" : "+"}
                    </span>
                  </button>
                  {activeSettingSection === "persona" && (
                    <div className="border-t border-[#143E6F]/10 p-5">
                      <PersonaPicker
                        heading={personaText("profile.heading")}
                        initialCategory={persona?.category ?? null}
                        source="profile"
                        onPicked={() => {
                          toast.success(personaText("profile.saved"));
                          setActiveSettingSection(null);
                        }}
                      />
                    </div>
                  )}
                </div>

                <div className="border border-[#143E6F]/20 rounded-xl">
                  <button
                    onClick={() =>
                      setActiveSettingSection((prev) =>
                        prev === "language" ? null : "language",
                      )
                    }
                    className="w-full px-5 py-4 flex items-center justify-between text-left"
                  >
                    <div>
                      <h4 className="text-lg font-semibold text-[#143E6F]">
                        {t("language.settings")}
                      </h4>
                      <p className="mt-1 text-sm text-gray-500">
                        {t("language.description")}
                      </p>
                    </div>
                    <span className="text-[#143E6F]">
                      {activeSettingSection === "language" ? "-" : "+"}
                    </span>
                  </button>
                  {activeSettingSection === "language" && (
                    <div className="border-t border-[#143E6F]/10 p-5 space-y-3">
                      <LanguagePicker
                        value={
                          preferredLocale ??
                          (user?.onboarding_organization_id ? null : "en")
                        }
                        onChange={(next) => void handleLocaleChange(next)}
                        disabled={isSavingLocale}
                        allowOrganizationDefault={Boolean(
                          user?.onboarding_organization_id,
                        )}
                      />
                      {isSavingLocale && (
                        <p className="text-sm text-gray-500">
                          {t("language.saving")}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <div className="border border-[#143E6F]/20 rounded-xl">
                  <button
                    onClick={() =>
                      setActiveSettingSection((prev) =>
                        prev === "profile" ? null : "profile",
                      )
                    }
                    className="w-full px-5 py-4 flex items-center justify-between text-left"
                  >
                    <h4 className="text-lg font-semibold text-[#143E6F]">
                      {uiText("mfec2ac0f4cf167e3")}
                    </h4>
                    <span className="text-[#143E6F]">
                      {activeSettingSection === "profile" ? "-" : "+"}
                    </span>
                  </button>
                  {activeSettingSection === "profile" && (
                    <div className="border-t border-[#143E6F]/10 p-5 space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {uiText("mdcd1d5223f73b3a9")}
                        </label>
                        <input
                          type="text"
                          name="full_name"
                          value={formData.full_name}
                          onChange={handleInputChange}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {uiText("m3933b1802161254f")}
                        </label>
                        <textarea
                          name="bio"
                          value={formData.bio}
                          onChange={handleInputChange}
                          rows={4}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          {uiText("m003d1aeefd3feda6")}
                        </label>
                        <div className="flex gap-2 flex-wrap">
                          {avatarColors.map((color) => (
                            <button
                              key={color}
                              type="button"
                              onClick={() =>
                                setFormData((prev) => ({
                                  ...prev,
                                  avatar_color: color,
                                }))
                              }
                              className={`w-9 h-9 rounded-full border-2 ${
                                formData.avatar_color === color
                                  ? "border-[#143E6F]"
                                  : "border-transparent"
                              }`}
                              style={{ backgroundColor: color }}
                            />
                          ))}
                        </div>
                      </div>
                      <button
                        onClick={handleSaveProfile}
                        disabled={isSaving}
                        className="w-full bg-[#143E6F] text-white py-2 rounded-lg hover:bg-[#0f2f54] transition-colors disabled:opacity-50"
                      >
                        {isSaving
                          ? uiText("mdc85af8f2b1d0d67")
                          : saveSuccess
                            ? uiText("mb5c120b316c237a0")
                            : uiText("m09d0725ba3e9d186")}
                      </button>
                    </div>
                  )}
                </div>

                <div className="border border-[#143E6F]/20 rounded-xl">
                  <button
                    onClick={() =>
                      setActiveSettingSection((prev) =>
                        prev === "account" ? null : "account",
                      )
                    }
                    className="w-full px-5 py-4 flex items-center justify-between text-left"
                  >
                    <h4 className="text-lg font-semibold text-[#143E6F]">
                      {uiText("m7e1b0d5641f2640c")}
                    </h4>
                    <span className="text-[#143E6F]">
                      {activeSettingSection === "account" ? "-" : "+"}
                    </span>
                  </button>
                  {activeSettingSection === "account" && (
                    <div className="border-t border-[#143E6F]/10 p-5 space-y-4">
                      <button
                        onClick={handleRequestPasswordReset}
                        className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                      >
                        <p className="font-medium text-gray-900">
                          {uiText("m3f9c991f63a9a376")}
                        </p>
                        <p className="text-sm text-gray-500">
                          {uiText("med9b989fde608b9b")}
                        </p>
                      </button>

                      <div className="border border-gray-200 rounded-lg p-4 space-y-3">
                        <label className="block text-sm font-medium text-gray-700">
                          {uiText("m5f8ce4b504c93564")}
                        </label>
                        <input
                          type="email"
                          value={newEmail}
                          onChange={(event) => setNewEmail(event.target.value)}
                          placeholder={uiText("m8a77fe02a1966fdb")}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                        />
                        <button
                          onClick={handleUpdateEmail}
                          className="w-full bg-[#143E6F] text-white py-2 rounded-lg hover:bg-[#0f2f54] transition-colors"
                        >
                          {uiText("meb42487f94ff995b")}
                        </button>
                        {emailChangePending && (
                          <div className="space-y-2">
                            <input
                              type="text"
                              value={emailOtp}
                              onChange={(event) =>
                                setEmailOtp(event.target.value)
                              }
                              placeholder={uiText("m78d5714a87cb6948")}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#143E6F]"
                            />
                            <button
                              onClick={handleVerifyEmailChange}
                              className="w-full border border-[#143E6F] text-[#143E6F] py-2 rounded-lg hover:bg-[#143E6F]/10 transition-colors"
                            >
                              {uiText("me89a77e7fe58a6d1")}
                            </button>
                          </div>
                        )}
                      </div>

                      <button
                        onClick={() => setShowDeleteConfirm(true)}
                        className="w-full text-left px-4 py-3 rounded-lg border border-red-300 hover:bg-red-50 transition-colors"
                      >
                        <p className="font-medium text-red-600">
                          {uiText("ma2e20a33570001ae")}
                        </p>
                        <p className="text-sm text-red-500">
                          {uiText("mf551c1f211804b74")}
                        </p>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>

        {showLogoutConfirm && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => !isLoggingOut && setShowLogoutConfirm(false)}
          >
            <div
              className="bg-white rounded-2xl w-full max-w-md p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-semibold text-center mb-4 text-gray-900">
                {uiText("m01fb32f707d76eec")}
              </h2>
              <p className="text-gray-600 text-center mb-6">
                {uiText("m067f10b734111433")}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowLogoutConfirm(false)}
                  disabled={isLoggingOut}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {uiText("m19766ed6ccb2f4a3")}
                </button>
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="flex-1 bg-[#143E6F] text-white py-2.5 rounded-lg font-medium hover:bg-[#0f2f54] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoggingOut
                    ? uiText("md0c59d736b1322a3")
                    : uiText("md0527e4b3d658351")}
                </button>
              </div>
            </div>
          </div>
        )}
        {showDeleteConfirm && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
            onClick={() => setShowDeleteConfirm(false)}
          >
            <div
              className="bg-white rounded-2xl w-full max-w-md p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-xl font-semibold text-center mb-4 text-gray-900">
                {uiText("mc031bf992e172f57")}
              </h2>
              <p className="text-gray-600 text-center mb-6">
                {uiText("mf0ba927c8e57c2cb")}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  className="flex-1 border border-gray-300 text-gray-700 py-2.5 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                >
                  {uiText("m19766ed6ccb2f4a3")}
                </button>
                <button
                  onClick={handleDeleteAccount}
                  className="flex-1 bg-red-600 text-white py-2.5 rounded-lg font-medium hover:bg-red-700 transition-colors"
                >
                  {uiText("me2d0a54968ead24e")}
                </button>
              </div>
            </div>
          </div>
        )}
      </RequireAuth>

      <Footer />
    </div>
  );
}
