import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import toast from "react-hot-toast";
import {
  User,
  Shield,
  CreditCard,
  UserCheck,
  Mail,
  KeyRound,
  Trash2,
  ExternalLink,
  Check,
  Edit3,
  AlertTriangle,
  Globe,
  MapPin,
  LogOut,
  ChevronRight,
} from "lucide-react";
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
import { type SupportedLocale } from "@shared/config/locale";
import { usePersonaCopy } from "@features/persona/hooks/usePersonaCopy";
import {
  archivo,
  Kicker,
  BTN_PRIMARY,
  BTN_GHOST,
  BTN_BASE,
} from "@shared/ui/quizwerk";

type ProfileTab = "overview" | "persona" | "billing" | "security" | "language";

export default function ProfilePage() {
  const { t: uiText, i18n } = useTranslation("ui");
  const { t } = useTranslation();
  const { t: personaText } = usePersonaCopy();
  const { preferredLocale, setPreferredLocale } = useLocale();
  const [isSavingLocale, setIsSavingLocale] = useState(false);

  const { user, isLoading, logout, refreshUser } = useAuth();
  const { persona, definition, categoryDefinition } = usePersona();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<ProfileTab>("overview");
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState(false);

  const [newEmail, setNewEmail] = useState("");
  const [emailOtp, setEmailOtp] = useState("");
  const [emailChangePending, setEmailChangePending] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [publicProfile, setPublicProfile] = useState(false);

  const [paymentNotice, setPaymentNotice] = useState<{
    type: "cancelled" | "success";
    message: string;
  } | null>(null);
  const [isOpeningPortal, setIsOpeningPortal] = useState(false);
  const [billingSummary, setBillingSummary] =
    useState<SubscriptionSummary | null>(null);

  const [formData, setFormData] = useState({
    full_name: "",
    bio: "",
    location: "",
    website: "",
    avatar_color: "#143E6F",
  });

  // Skip syncing while editing so a background refreshUser() doesn't
  // overwrite unsaved changes.
  useEffect(() => {
    if (user && !isEditing) {
      setFormData({
        full_name: user.full_name || "",
        bio: user.bio || "",
        location: user.location || "",
        website: user.website || "",
        avatar_color: user.avatar_color || "#143E6F",
      });
    }
  }, [user, isEditing]);

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
    if (!user?.stripe_customer_id || user.current_period_end) return;
    void getSubscriptionSummary()
      .then(setBillingSummary)
      .catch(() => {});
  }, [user?.current_period_end, user?.stripe_customer_id]);

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
        message: uiText("profile.paymentSuccess"),
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
              uiText("profile.paymentRefreshFailed"),
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
        message: uiText("profile.paymentCancelled"),
      });
      void router.replace("/profile", undefined, { shallow: true });
    }
  }, [refreshUser, router, router.isReady, router.query.payment]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setSaveError("");
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      setShowLogoutConfirm(false);
      router.push("/");
    } catch {
      toast.error(uiText("md64206ce225f573b"));
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleSaveProfile = async () => {
    if (user?.is_verified === false) {
      toast.error(uiText("m10cf11c897a08692"));
      return;
    }
    setIsSaving(true);
    setSaveError("");
    try {
      if (user) {
        await updateProfile({
          full_name: formData.full_name,
          bio: formData.bio,
          location: formData.location,
          website: formData.website,
          avatar_color: formData.avatar_color,
        });
        await refreshUser();
        setSaveSuccess(true);
        setIsEditing(false);
        toast.success(uiText("me71daf5f6cf7b62d"));
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
      toast.error(error.message || uiText("meeb7276dab30a337"));
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
      toast.success(uiText("m30746b43a4e1a262"));
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
      toast.success(uiText("mf65c2dd173fc5063"));
      await logout();
    } catch (error: any) {
      toast.error(error?.message || uiText("m83326cc97ff9fac2"));
    }
  };

  const handleManageSubscription = async () => {
    try {
      setIsOpeningPortal(true);
      const { portal_url } = await createPortalSession();
      window.location.assign(portal_url);
    } catch (error: any) {
      toast.error(
        getBillingErrorMessage(error, uiText("profile.portalFailed")),
      );
    } finally {
      setIsOpeningPortal(false);
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
    const value = plan || "free";
    return t(`values.${value}`, {
      defaultValue: value.charAt(0).toUpperCase() + value.slice(1),
    });
  };

  const formatStatusLabel = (status?: string) => {
    const value = status || "inactive";
    return t(`values.${value}`, {
      defaultValue: value
        .split("_")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" "),
    });
  };

  const subscriptionStatusClassName =
    billingStatus === "active"
      ? "bg-emerald-100 text-emerald-800 border-emerald-300"
      : billingStatus === "past_due"
        ? "bg-amber-100 text-amber-800 border-amber-300"
        : "bg-slate-100 text-slate-700 border-slate-300";

  const personaLabel =
    categoryDefinition && definition
      ? `${categoryDefinition.label} · ${definition.label}`
      : personaText("profile.unset");

  if (isLoading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-10 w-10 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          <p className="mt-4 text-sm font-bold text-ink/70">
            {uiText("m4a47f12d23c4a6bf")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex min-h-screen flex-col overflow-x-hidden bg-paper text-ink ${archivo.className}`}
    >
      <NavBar />

      <RequireAuth
        title={uiText("m991bfa015514f9d5")}
        description={uiText("m0bbb194809df9769")}
      >
        <main className="mx-auto w-full max-w-5xl px-4 sm:px-6 flex-1 py-[clamp(24px,5vw,48px)]">
          {/* Header */}
          <div>
            <Kicker>{uiText("m939eccfb6dd7133a")}</Kicker>
            <h1 className="text-[clamp(28px,6vw,40px)] font-extrabold leading-tight tracking-[-0.025em] text-ink">
              {uiText("m4f1063c95669d708")}
            </h1>
            <p className="mt-1.5 max-w-2xl text-[clamp(13px,2vw,15px)] leading-relaxed text-ink/70">
              {uiText("m9c012bb430e8a983")}
            </p>
          </div>

          {/* Feedback Notices */}
          {paymentNotice && (
            <div
              className={`mt-4 sm:mt-6 border-l-4 p-3 sm:p-4 ${
                paymentNotice.type === "success"
                  ? "border-emerald-600 bg-emerald-50 text-emerald-900"
                  : "border-amber-500 bg-amber-50 text-amber-900"
              }`}
            >
              <p className="text-xs sm:text-sm font-semibold">
                {paymentNotice.message}
              </p>
            </div>
          )}

          {saveSuccess && (
            <div className="mt-4 sm:mt-6 border-l-4 border-emerald-600 bg-emerald-50 p-3 sm:p-4 text-emerald-900">
              <p className="text-xs sm:text-sm font-semibold">
                {uiText("m6ccf8b7d69b8b021")}
              </p>
            </div>
          )}

          {saveError && (
            <div className="mt-4 sm:mt-6 border-l-4 border-rose-600 bg-rose-50 p-3 sm:p-4 text-rose-900">
              <p className="text-xs sm:text-sm font-semibold">{saveError}</p>
            </div>
          )}

          {/* Identity Hero Banner */}
          <div className="mt-6 sm:mt-8 border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 w-full max-w-full">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 sm:gap-6">
              <div className="flex items-start sm:items-center gap-3.5 sm:gap-5 min-w-0">
                <div
                  className="flex h-12 w-12 sm:h-20 sm:w-20 flex-shrink-0 items-center justify-center text-white text-xl sm:text-3xl font-black"
                  style={{ backgroundColor: formData.avatar_color }}
                  data-testid="profile-avatar"
                >
                  {user?.username?.charAt(0).toUpperCase() || "U"}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 flex-wrap items-center gap-1.5 sm:gap-2.5">
                    <h2 className="min-w-0 break-words text-[clamp(18px,4vw,24px)] font-extrabold text-ink">
                      {formData.full_name ||
                        user?.username ||
                        uiText("mb512d97e7cbf97c2")}
                    </h2>
                    {user?.is_verified ? (
                      <span className="inline-flex items-center gap-1 border border-emerald-300 bg-emerald-50 px-1.5 sm:px-2 py-0.5 text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-emerald-800">
                        <Check className="h-2.5 w-2.5 sm:h-3 sm:w-3" />{" "}
                        {uiText("m4f7838402f37674e")}
                      </span>
                    ) : null}
                  </div>

                  <p className="mt-0.5 text-xs sm:text-sm font-mono text-ink/60 break-all">
                    @{user?.username || uiText("m04f8996da763b7a9")} ·{" "}
                    {user?.email}
                  </p>

                  <div className="mt-2.5 sm:mt-3 flex flex-wrap items-center gap-1.5 sm:gap-2">
                    <button
                      type="button"
                      onClick={() => setActiveTab("persona")}
                      className="inline-flex min-w-0 max-w-full items-center gap-1.5 border border-brand/20 bg-brand-50/60 px-2 py-1 text-[11px] font-bold text-brand-700 transition-colors hover:bg-brand-100 sm:px-2.5 sm:text-xs"
                    >
                      <span className="h-1.5 w-1.5 sm:h-2 sm:w-2 bg-brand flex-shrink-0" />
                      <span className="min-w-0 truncate">
                        {uiText("profile.roleSummary", { role: personaLabel })}
                      </span>
                      <ChevronRight className="h-3 w-3 text-brand flex-shrink-0" />
                    </button>

                    <span
                      className={`inline-flex max-w-full items-center border px-2 py-1 text-[11px] font-bold sm:px-2.5 sm:text-xs ${subscriptionStatusClassName}`}
                    >
                      {uiText("profile.planSummary", {
                        plan: formatPlanLabel(billingPlan),
                        status: formatStatusLabel(billingStatus),
                      })}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row w-full sm:w-auto items-stretch sm:items-center gap-2 sm:gap-3 mt-2 sm:mt-0">
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab("overview");
                    if (isEditing) {
                      handleCancelEdit();
                    } else {
                      setIsEditing(true);
                    }
                  }}
                  className={`w-full sm:w-auto justify-center min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm px-3 py-2 ${
                    isEditing ? BTN_GHOST : BTN_PRIMARY
                  }`}
                >
                  <Edit3 className="mr-1.5 sm:mr-2 h-3.5 w-3.5 sm:h-4 sm:w-4" />
                  {isEditing
                    ? uiText("mfddcfdf8d5f404e1")
                    : uiText("mfec2ac0f4cf167e3")}
                </button>

                <button
                  type="button"
                  onClick={() => setShowLogoutConfirm(true)}
                  className={`w-full sm:w-auto justify-center min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm px-3 py-2 ${BTN_GHOST} text-rose-700 hover:bg-rose-50`}
                  aria-label={uiText("m48f0d3d397d49f13")}
                >
                  <LogOut className="mr-1.5 sm:mr-2 h-3.5 w-3.5 sm:h-4 sm:w-4" />
                  {uiText("m0b184bc5d5341998")}
                </button>
              </div>
            </div>
          </div>

          {/* Tab Navigation: 2-Column Responsive Grid on Mobile, Flex on Desktop */}
          <div className="mt-6 sm:mt-8 border-b-0 sm:border-b-2 sm:border-divider">
            <nav
              className="grid grid-cols-2 gap-2 sm:flex sm:space-x-4 md:space-x-8"
              aria-label={uiText("m8e5ea509893e6dfd")}
            >
              {[
                {
                  id: "overview",
                  label: uiText("mb863a343d85adb8f"),
                  icon: User,
                },
                {
                  id: "persona",
                  label: uiText("m75dafd90c38333f0"),
                  icon: UserCheck,
                },
                {
                  id: "billing",
                  label: uiText("m9e47ba56d3c4c003"),
                  icon: CreditCard,
                },
                {
                  id: "security",
                  label: uiText("m528396ce9399d0e9"),
                  icon: Shield,
                },
                { id: "language", label: t("language.settings"), icon: Globe },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as ProfileTab)}
                    className={`inline-flex items-center justify-center sm:justify-start gap-1.5 sm:gap-2 p-2.5 sm:px-3 sm:py-3 text-[11px] min-[360px]:text-xs sm:text-sm font-extrabold transition-colors border-2 sm:border-0 sm:border-b-2 ${
                      isActive
                        ? "border-brand bg-brand-50/60 text-brand sm:bg-transparent sm:border-brand"
                        : "border-divider bg-white text-ink/70 hover:bg-ink/[0.03] hover:text-ink sm:border-transparent sm:bg-transparent sm:hover:border-ink/20"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4 flex-shrink-0" />
                    <span className="truncate sm:whitespace-nowrap">
                      {tab.label}
                    </span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Tab Content Areas */}
          <div className="mt-6 sm:mt-8">
            {/* TAB 1: OVERVIEW & DETAILS */}
            {activeTab === "overview" && (
              <div className="border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 w-full max-w-full">
                <div className="flex flex-wrap items-center justify-between border-b-2 border-divider pb-3 sm:pb-4 mb-4 sm:mb-6 gap-2">
                  <div>
                    <h3 className="text-lg sm:text-xl font-extrabold text-ink">
                      {uiText("mc4b37e84b553d29b")}
                    </h3>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                      {uiText("m131a59ae0aaedf15")}
                    </p>
                  </div>
                  {!isEditing && (
                    <button
                      type="button"
                      onClick={() => setIsEditing(true)}
                      className={`${BTN_GHOST} text-xs sm:text-sm min-h-[36px] sm:min-h-[44px] px-3 py-1.5`}
                    >
                      <Edit3 className="mr-1.5 h-3.5 w-3.5" />
                      {uiText("m8cfa48f3b9db69e9")}
                    </button>
                  )}
                </div>

                {isEditing ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSaveProfile();
                    }}
                    className="space-y-4 sm:space-y-6 max-w-5xl w-full"
                  >
                    <div>
                      <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                        {uiText("m8e00cdf71fa7cc76")}
                      </label>
                      <input
                        type="text"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleInputChange}
                        placeholder={uiText("mb087835b98c385df")}
                        className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1.5">
                        {uiText("me068ba27a3cff081")}
                      </label>
                      <div className="flex flex-wrap gap-2 sm:gap-2.5">
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
                            className={`h-7 w-7 sm:h-8 sm:w-8 rounded-full transition-transform ${
                              formData.avatar_color === color
                                ? "ring-2 ring-brand ring-offset-2 scale-110"
                                : "hover:scale-105"
                            }`}
                            style={{ backgroundColor: color }}
                            aria-label={uiText("m02a34b8afdf4e11e", {
                              value0: color,
                            })}
                          />
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                        {uiText("m3933b1802161254f")}
                      </label>
                      <textarea
                        name="bio"
                        rows={3}
                        value={formData.bio}
                        onChange={handleInputChange}
                        maxLength={500}
                        placeholder={uiText("mddf4e9ad78bea56c")}
                        className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                      />
                      <p className="mt-1 text-right text-[11px] text-ink/50">
                        {formData.bio.length}/500 characters
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <div>
                        <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                          {uiText("m15b61974b2707a7b")}
                        </label>
                        <input
                          type="text"
                          name="location"
                          value={formData.location}
                          onChange={handleInputChange}
                          placeholder={uiText("ma7bc8816f26258d2")}
                          className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                          {uiText("mb5a229ac8becc603")}
                        </label>
                        <input
                          type="url"
                          name="website"
                          value={formData.website}
                          onChange={handleInputChange}
                          placeholder="https://example.com"
                          className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                        />
                      </div>
                    </div>

                    <div className="border-t-2 border-divider pt-3 sm:pt-4">
                      <label className="flex items-center gap-2.5 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={publicProfile}
                          onChange={(e) => setPublicProfile(e.target.checked)}
                          className="h-4 w-4 accent-brand flex-shrink-0"
                        />
                        <span className="text-xs sm:text-sm font-bold text-ink">
                          {uiText("me7d0707625d617cd")}
                        </span>
                      </label>
                      <p className="mt-1 text-[11px] sm:text-xs text-ink/60 pl-6">
                        {uiText("ma2c8c5485b5e3706")}
                      </p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 pt-3 sm:pt-4 border-t-2 border-divider">
                      <button
                        type="submit"
                        disabled={isSaving}
                        className={`${BTN_PRIMARY} w-full sm:w-auto min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                      >
                        {isSaving
                          ? uiText("m86c6e0d74cc948c0")
                          : uiText("m35322b5bb5a218a1")}
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelEdit}
                        disabled={isSaving}
                        className={`${BTN_GHOST} w-full sm:w-auto min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                      >
                        {uiText("m19766ed6ccb2f4a3")}
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="space-y-4 sm:space-y-6 max-w-5xl w-full">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-6">
                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          {uiText("m8e00cdf71fa7cc76")}
                        </span>
                        <p className="mt-1 break-words text-sm font-extrabold text-ink sm:text-base">
                          {formData.full_name || uiText("m4895f73177ab5d67")}
                        </p>
                      </div>

                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          {uiText("me3b89e9d33f88e52")}
                        </span>
                        <p className="mt-1 break-all font-mono text-sm font-bold text-ink sm:text-base">
                          @{user?.username || "N/A"}
                        </p>
                      </div>

                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          {uiText("m09bf25ef30833633")}
                        </span>
                        <p className="mt-1 text-xs sm:text-base font-mono text-ink break-all">
                          {user?.email || "N/A"}
                        </p>
                      </div>

                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          {uiText("m15b61974b2707a7b")}
                        </span>
                        <p className="mt-1 flex min-w-0 items-center gap-1.5 text-sm text-ink sm:text-base">
                          <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-ink/40 flex-shrink-0" />
                          <span className="min-w-0 break-words">
                            {formData.location || uiText("m4895f73177ab5d67")}
                          </span>
                        </p>
                      </div>
                    </div>

                    <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                      <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                        {uiText("m3933b1802161254f")}
                      </span>
                      <p className="mt-1 text-xs sm:text-sm text-ink leading-relaxed break-words">
                        {formData.bio || uiText("mecdab25ab8ace098")}
                      </p>
                    </div>

                    <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                      <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                        {uiText("m9a3dd7f603c2f4fe")}
                      </span>
                      <div className="mt-1 flex items-center gap-2 text-xs sm:text-sm break-all">
                        <Globe className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-ink/40 flex-shrink-0" />
                        {formData.website ? (
                          <a
                            href={formData.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex min-w-0 items-center gap-1 font-bold text-brand hover:underline"
                          >
                            <span className="min-w-0 break-all">
                              {formData.website}
                            </span>
                            <ExternalLink className="h-3 w-3 flex-shrink-0" />
                          </a>
                        ) : (
                          <span className="text-ink/60">
                            {uiText("m89ce7824f4f4022c")}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === "language" && (
              <section className="border-2 border-divider bg-white p-4 sm:p-6 space-y-4">
                <h3 className="text-lg font-extrabold">
                  {t("language.settings")}
                </h3>
                <p className="text-sm text-ink/70">
                  {t("language.description")}
                </p>
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
                {isSavingLocale && <p role="status">{t("language.saving")}</p>}
              </section>
            )}

            {/* TAB 2: ROLE & PERSONA */}
            {activeTab === "persona" && (
              <div className="border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 space-y-6 sm:space-y-8 w-full max-w-full">
                <div>
                  <h3 className="text-lg sm:text-xl font-extrabold text-ink">
                    {uiText("ma57809d16ce7c487")}
                  </h3>
                  <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                    {uiText("md8a72dbc4510cebb")}
                  </p>
                </div>

                {/* Current Persona Summary Card */}
                <div className="border-2 border-brand/30 bg-brand-50/40 p-3.5 sm:p-5 w-full max-w-full">
                  <div className="flex flex-wrap items-center justify-between gap-2.5">
                    <div className="min-w-0 flex-1">
                      <span className="text-[10px] sm:text-xs font-extrabold uppercase tracking-widest text-brand-700">
                        {uiText("me330395f7a37f8dd")}
                      </span>
                      <h4 className="mt-0.5 break-words text-xl font-black text-ink sm:mt-1 sm:text-2xl">
                        {personaLabel}
                      </h4>
                    </div>
                    <span className="inline-flex items-center gap-1 bg-brand px-2 sm:px-3 py-1 text-[10px] sm:text-xs font-extrabold uppercase tracking-wider text-paper flex-shrink-0">
                      <Check className="h-3 w-3 sm:h-3.5 sm:w-3.5" />{" "}
                      {uiText("m4a6bf58744a593ee")}
                    </span>
                  </div>

                  {definition && (
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-4 border-t-2 border-brand/20 pt-3 sm:pt-4 text-xs">
                      <div className="break-words">
                        <span className="font-bold text-ink/60">
                          {uiText("m26c67fd6b21830dc")}
                        </span>
                        <p className="mt-0.5 font-medium text-ink">
                          {definition.description}
                        </p>
                      </div>
                      <div className="break-words">
                        <span className="font-bold text-ink/60">
                          {uiText("m0c97d771aad5d18a")}
                        </span>
                        <p className="mt-0.5 font-medium text-ink">
                          {definition.defaultTopic}
                        </p>
                      </div>
                      <div className="break-words">
                        <span className="font-bold text-ink/60">
                          {uiText("m2c143f33031c4431")}
                        </span>
                        <p className="mt-0.5 font-medium text-ink">
                          {uiText("profile.generationPreset", {
                            audience: personaText(
                              `audiences.${definition.generationDefaults.audienceType}`,
                            ),
                            difficulty: personaText(
                              `difficulty.${definition.generationDefaults.difficultyLevel}`,
                            ),
                          })}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Switch Persona Picker */}
                <div className="border-t-2 border-divider pt-4 sm:pt-6 w-full max-w-full">
                  <div className="mb-4 sm:mb-6">
                    <h4 className="text-base sm:text-lg font-extrabold text-ink">
                      {uiText("m54331fcf1227f45f")}
                    </h4>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                      {uiText("m46c6a1161b996753")}
                    </p>
                  </div>
                  <PersonaPicker
                    heading={uiText("m245e8c9089ecddc6")}
                    onPicked={() => {
                      toast.success(uiText("m1d4d5ccd57d1d120"));
                    }}
                  />
                </div>
              </div>
            )}

            {/* TAB 3: SUBSCRIPTION & BILLING */}
            {activeTab === "billing" && (
              <div className="border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 space-y-4 sm:space-y-6 w-full max-w-full">
                <div className="border-b-2 border-divider pb-3 sm:pb-4">
                  <h3 className="text-lg sm:text-xl font-extrabold text-ink">
                    {uiText("m9e47ba56d3c4c003")}
                  </h3>
                  <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                    {uiText("mf8fb4e09276ef0d2")}
                  </p>
                </div>

                <div className="border-2 border-divider p-4 sm:p-6 bg-paper/30 w-full max-w-full">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                        {uiText("ma8fd423db9423196")}
                      </span>
                      <h4 className="text-xl sm:text-2xl font-black text-ink mt-0.5">
                        {uiText("m3e0e44cf0338ceb7", {
                          value0: formatPlanLabel(billingPlan),
                        })}
                      </h4>
                      <div className="mt-2 flex items-center gap-2">
                        <span
                          className={`inline-flex border px-2 sm:px-2.5 py-0.5 text-[11px] sm:text-xs font-extrabold uppercase tracking-wide ${subscriptionStatusClassName}`}
                        >
                          {uiText("md617370d57781737", {
                            value0: formatStatusLabel(billingStatus),
                          })}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3">
                      {hasBillingPortalAccess ? (
                        <button
                          type="button"
                          onClick={handleManageSubscription}
                          disabled={isOpeningPortal}
                          className={`${BTN_PRIMARY} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                        >
                          {isOpeningPortal
                            ? uiText("maa987d702e9696af")
                            : uiText("mcbc4ef9225a090f7")}
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => router.push("/#pricing")}
                          className={`${BTN_PRIMARY} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                        >
                          {uiText("m1f033eb27e6cf7a7")}
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => router.push("/billing_history")}
                        className={`${BTN_GHOST} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                      >
                        {uiText("m5ade08611d1f4322")}
                      </button>
                    </div>
                  </div>

                  <p className="mt-4 text-xs text-ink/70 border-t-2 border-divider pt-3 sm:pt-4 leading-relaxed">
                    {billingRenewalDate
                      ? uiText("mfcbd7e978aaefbb2", {
                          value0: new Date(
                            billingRenewalDate,
                          ).toLocaleDateString(i18n.language),
                        })
                      : billingPlan === "free"
                        ? uiText("mf999260a1a3cfca7")
                        : uiText("m5ef7fe9fe48fb720")}
                  </p>
                </div>
              </div>
            )}

            {/* TAB 4: SECURITY & ACCOUNT */}
            {activeTab === "security" && (
              <div className="border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 space-y-6 sm:space-y-8 w-full max-w-full">
                <div className="border-b-2 border-divider pb-3 sm:pb-4">
                  <h3 className="text-lg sm:text-xl font-extrabold text-ink">
                    {uiText("m12b039a331fe85eb")}
                  </h3>
                  <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                    {uiText("m5043da30e1031a74")}
                  </p>
                </div>

                {/* Password Reset */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 border-b-2 border-divider pb-4 sm:pb-6">
                  <div>
                    <h4 className="text-sm sm:text-base font-extrabold text-ink flex items-center gap-2">
                      <KeyRound className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-brand" />{" "}
                      {uiText("mb852fe243f49516a")}
                    </h4>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                      {uiText("m55cb89fc3f08c4cb")}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRequestPasswordReset}
                    className={`${BTN_GHOST} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                  >
                    {uiText("m4e70f1fd24babdea")}
                  </button>
                </div>

                {/* Email Update */}
                <div className="border-b-2 border-divider pb-4 sm:pb-6 space-y-3 sm:space-y-4">
                  <div>
                    <h4 className="text-sm sm:text-base font-extrabold text-ink flex items-center gap-2">
                      <Mail className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-brand" />{" "}
                      {uiText("m7ad9e11955b60c01")}
                    </h4>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5 break-all">
                      {uiText("m3669515a2cc33fd9")}
                      <strong className="font-mono text-ink">
                        {user?.email}
                      </strong>
                    </p>
                  </div>

                  <div className="max-w-md space-y-3 w-full">
                    <input
                      type="email"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      placeholder={uiText("m51e6ebc2f5fdcc13")}
                      className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleUpdateEmail}
                      className={`${BTN_PRIMARY} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                    >
                      {uiText("m2bd7bfd7b3314b9b")}
                    </button>

                    {emailChangePending && (
                      <div className="mt-3 sm:mt-4 p-3 sm:p-4 border-2 border-brand/30 bg-brand-50/50 space-y-3">
                        <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-brand-900">
                          {uiText("m6635da66ff0ead5e")}
                        </label>
                        <input
                          type="text"
                          value={emailOtp}
                          onChange={(e) => setEmailOtp(e.target.value)}
                          placeholder={uiText("m3ee75029c70e284c")}
                          className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={handleVerifyEmailChange}
                          className={`${BTN_PRIMARY} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                        >
                          {uiText("mb93bce9696eee559")}
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Danger Zone */}
                <div className="border-2 border-rose-200 bg-rose-50/40 p-3.5 sm:p-5 w-full max-w-full">
                  <h4 className="text-sm sm:text-base font-extrabold text-rose-800 flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-rose-700" />{" "}
                    {uiText("m60245e93718bc0c9")}
                  </h4>
                  <p className="mt-1 text-[11px] sm:text-xs text-rose-700 leading-relaxed max-w-2xl">
                    {uiText("m1677438c268ed2a4")}
                  </p>
                  <div className="mt-3 sm:mt-4">
                    <button
                      type="button"
                      onClick={() => setShowDeleteConfirm(true)}
                      className={`${BTN_BASE} border-2 border-rose-700 bg-rose-600 text-white hover:bg-rose-700 w-full sm:w-auto min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm px-3 py-2`}
                    >
                      <Trash2 className="mr-1.5 h-3.5 w-3.5 sm:h-4 sm:w-4" />
                      {uiText("mc031bf992e172f57")}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </main>

        {/* Confirmation Modals */}
        {showLogoutConfirm && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
            onClick={() => !isLoggingOut && setShowLogoutConfirm(false)}
          >
            <div
              className="w-full max-w-md border-2 border-ink bg-white p-4 sm:p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg sm:text-xl font-extrabold text-ink">
                {uiText("mcc39c00b51a876a1")}
              </h3>
              <p className="mt-2 text-xs sm:text-sm text-ink/70">
                {uiText("ma03ea8ce539bb718")}
              </p>
              <div className="mt-6 flex flex-col sm:flex-row gap-2 sm:gap-3">
                <button
                  type="button"
                  onClick={() => setShowLogoutConfirm(false)}
                  disabled={isLoggingOut}
                  className={`${BTN_GHOST} flex-1 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  {uiText("m19766ed6ccb2f4a3")}
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className={`${BTN_PRIMARY} flex-1 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  {isLoggingOut
                    ? uiText("m0436231679a0cb2b")
                    : uiText("m0b184bc5d5341998")}
                </button>
              </div>
            </div>
          </div>
        )}

        {showDeleteConfirm && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-ink/60 p-4"
            onClick={() => setShowDeleteConfirm(false)}
          >
            <div
              className="w-full max-w-md border-2 border-rose-600 bg-white p-4 sm:p-8"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg sm:text-xl font-extrabold text-rose-900 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 sm:h-5 sm:w-5 text-rose-600" />
                {uiText("m22b957a6205bc259")}
              </h3>
              <p className="mt-2 text-xs sm:text-sm text-ink/70">
                {uiText("meddf32a686ec5ba1")}
              </p>
              <div className="mt-6 flex flex-col sm:flex-row gap-2 sm:gap-3">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className={`${BTN_GHOST} flex-1 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  {uiText("m409890f3c4df8037")}
                </button>
                <button
                  type="button"
                  onClick={handleDeleteAccount}
                  className={`${BTN_BASE} flex-1 border-2 border-rose-700 bg-rose-600 text-white hover:bg-rose-700 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  {uiText("ma7f54311a3e625f5")}
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
