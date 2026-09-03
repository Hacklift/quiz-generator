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
import {
  archivo,
  Kicker,
  BTN_PRIMARY,
  BTN_GHOST,
  BTN_BASE,
  CONTAINER,
} from "@shared/ui/quizwerk";

type ProfileTab = "overview" | "persona" | "billing" | "security";

export default function ProfilePage() {
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

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await logout();
      setShowLogoutConfirm(false);
      router.push("/");
    } catch {
      toast.error("Failed to log out. Please try again.");
    } finally {
      setIsLoggingOut(false);
    }
  };

  const handleSaveProfile = async () => {
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
        setSaveSuccess(true);
        setIsEditing(false);
        toast.success("Profile saved successfully.");
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
      setSaveError(error.message || "Failed to update profile");
      toast.error(error.message || "Failed to update profile");
    } finally {
      setIsSaving(false);
    }
  };

  const handleRequestPasswordReset = () => {
    router.push("/auth/request-reset-password");
  };

  const handleUpdateEmail = async () => {
    if (!newEmail.trim()) {
      toast.error("Please enter a new email.");
      return;
    }
    try {
      await requestEmailChange(newEmail.trim());
      setEmailChangePending(true);
      toast.success("Verification code sent to your new email.");
    } catch (error: any) {
      toast.error(error?.message || "Failed to send verification email.");
    }
  };

  const handleVerifyEmailChange = async () => {
    if (!emailOtp.trim()) {
      toast.error("Enter the verification code.");
      return;
    }
    try {
      await verifyEmailChange(emailOtp.trim());
      setEmailChangePending(false);
      setEmailOtp("");
      setNewEmail("");
      await refreshUser();
      toast.success("Email updated successfully.");
    } catch (error: any) {
      toast.error(error?.message || "Failed to verify email.");
    }
  };

  const handleDeleteAccount = async () => {
    try {
      await deleteAccount();
      setShowDeleteConfirm(false);
      toast.success("Your account has been deleted.");
      await logout();
    } catch (error: any) {
      toast.error(error?.message || "Failed to delete account.");
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
    billingSummary?.subscription_status || user?.subscription_status || "inactive";
  const billingRenewalDate =
    billingSummary?.current_period_end || user?.current_period_end || null;
  const hasBillingPortalAccess = Boolean(
    billingSummary?.stripe_customer_id || user?.stripe_customer_id,
  );

  const formatPlanLabel = (plan?: string) => {
    if (!plan || plan === "free") return "Free";
    return plan.charAt(0).toUpperCase() + plan.slice(1);
  };

  const formatStatusLabel = (status?: string) => {
    if (!status || status === "inactive") return "Inactive";
    return status
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
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
      : "Not set";

  if (isLoading) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-10 w-10 animate-spin rounded-full border-2 border-brand border-t-transparent" />
          <p className="mt-4 text-sm font-bold text-ink/70">Loading profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex min-h-screen flex-col overflow-x-hidden bg-paper text-ink ${archivo.className}`}>
      <NavBar />

      <RequireAuth
        title="My Profile"
        description="Sign in to view and manage your profile."
      >
        <main className={`${CONTAINER} flex-1 py-[clamp(24px,5vw,48px)]`}>
          {/* Header */}
          <div>
            <Kicker>ACCOUNT & PROFILE</Kicker>
            <h1 className="text-[clamp(28px,6vw,40px)] font-extrabold leading-tight tracking-[-0.025em] text-ink">
              Profile Settings
            </h1>
            <p className="mt-1.5 max-w-2xl text-[clamp(13px,2vw,15px)] leading-relaxed text-ink/70">
              Manage your personal information, role persona, subscription plan,
              and account security settings.
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
              <p className="text-xs sm:text-sm font-semibold">{paymentNotice.message}</p>
            </div>
          )}

          {saveSuccess && (
            <div className="mt-4 sm:mt-6 border-l-4 border-emerald-600 bg-emerald-50 p-3 sm:p-4 text-emerald-900">
              <p className="text-xs sm:text-sm font-semibold">Profile updated successfully.</p>
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
                      {formData.full_name || user?.username || "User"}
                    </h2>
                    {user?.is_verified ? (
                      <span className="inline-flex items-center gap-1 border border-emerald-300 bg-emerald-50 px-1.5 sm:px-2 py-0.5 text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-emerald-800">
                        <Check className="h-2.5 w-2.5 sm:h-3 sm:w-3" /> Verified
                      </span>
                    ) : null}
                  </div>

                  <p className="mt-0.5 text-xs sm:text-sm font-mono text-ink/60 break-all">
                    @{user?.username || "user"} · {user?.email}
                  </p>

                  <div className="mt-2.5 sm:mt-3 flex flex-wrap items-center gap-1.5 sm:gap-2">
                    <button
                      type="button"
                      onClick={() => setActiveTab("persona")}
                      className="inline-flex min-w-0 max-w-full items-center gap-1.5 border border-brand/20 bg-brand-50/60 px-2 py-1 text-[11px] font-bold text-brand-700 transition-colors hover:bg-brand-100 sm:px-2.5 sm:text-xs"
                    >
                      <span className="h-1.5 w-1.5 sm:h-2 sm:w-2 bg-brand flex-shrink-0" />
                      <span className="min-w-0 truncate">Role: {personaLabel}</span>
                      <ChevronRight className="h-3 w-3 text-brand flex-shrink-0" />
                    </button>

                    <span
                      className={`inline-flex max-w-full items-center border px-2 py-1 text-[11px] font-bold sm:px-2.5 sm:text-xs ${subscriptionStatusClassName}`}
                    >
                      {formatPlanLabel(billingPlan)} Plan ({formatStatusLabel(billingStatus)})
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row w-full sm:w-auto items-stretch sm:items-center gap-2 sm:gap-3 mt-2 sm:mt-0">
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab("overview");
                    setIsEditing(!isEditing);
                  }}
                  className={`w-full sm:w-auto justify-center min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm px-3 py-2 ${
                    isEditing ? BTN_GHOST : BTN_PRIMARY
                  }`}
                >
                  <Edit3 className="mr-1.5 sm:mr-2 h-3.5 w-3.5 sm:h-4 sm:w-4" />
                  {isEditing ? "Cancel Edit" : "Edit Profile"}
                </button>

                <button
                  type="button"
                  onClick={() => setShowLogoutConfirm(true)}
                  className={`w-full sm:w-auto justify-center min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm px-3 py-2 ${BTN_GHOST} text-rose-700 hover:bg-rose-50`}
                  aria-label="Sign out"
                >
                  <LogOut className="mr-1.5 sm:mr-2 h-3.5 w-3.5 sm:h-4 sm:w-4" />
                  Sign Out
                </button>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="mt-6 overflow-x-auto border-b-2 border-divider sm:mt-8">
            <nav className="flex min-w-max space-x-1 sm:space-x-4 md:space-x-8" aria-label="Tabs">
              {[
                { id: "overview", label: "Overview & Details", icon: User },
                { id: "persona", label: "Role & Persona", icon: UserCheck },
                { id: "billing", label: "Subscription & Billing", icon: CreditCard },
                { id: "security", label: "Security & Account", icon: Shield },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as ProfileTab)}
                    className={`inline-flex items-center gap-1.5 sm:gap-2 border-b-2 px-2.5 sm:px-3 py-2.5 sm:py-3 text-xs sm:text-sm font-extrabold whitespace-nowrap transition-colors flex-shrink-0 ${
                      isActive
                        ? "border-brand text-brand"
                        : "border-transparent text-ink/60 hover:border-ink/20 hover:text-ink"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />
                    <span>{tab.label}</span>
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
                    <h3 className="text-lg sm:text-xl font-extrabold text-ink">Personal Information</h3>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                      Your identity and public profile presentation.
                    </p>
                  </div>
                  {!isEditing && (
                    <button
                      type="button"
                      onClick={() => setIsEditing(true)}
                      className={`${BTN_GHOST} text-xs sm:text-sm min-h-[36px] sm:min-h-[44px] px-3 py-1.5`}
                    >
                      <Edit3 className="mr-1.5 h-3.5 w-3.5" />
                      Edit Details
                    </button>
                  )}
                </div>

                {isEditing ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSaveProfile();
                    }}
                    className="space-y-4 sm:space-y-6 max-w-2xl w-full"
                  >
                    <div>
                      <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                        Full Name
                      </label>
                      <input
                        type="text"
                        name="full_name"
                        value={formData.full_name}
                        onChange={handleInputChange}
                        placeholder="e.g. Dr. Alex Morgan"
                        className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1.5">
                        Avatar Color Accent
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
                            aria-label={`Select avatar color ${color}`}
                          />
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                        Bio
                      </label>
                      <textarea
                        name="bio"
                        rows={3}
                        value={formData.bio}
                        onChange={handleInputChange}
                        maxLength={500}
                        placeholder="A brief summary of your background, teaching interests, or team focus..."
                        className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                      />
                      <p className="mt-1 text-right text-[11px] text-ink/50">
                        {formData.bio.length}/500 characters
                      </p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                      <div>
                        <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                          Location
                        </label>
                        <input
                          type="text"
                          name="location"
                          value={formData.location}
                          onChange={handleInputChange}
                          placeholder="City, Country"
                          className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/70 mb-1">
                          Website
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
                          Enable public profile page
                        </span>
                      </label>
                      <p className="mt-1 text-[11px] sm:text-xs text-ink/60 pl-6">
                        Allow learners or colleagues to view your public educator card.
                      </p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 pt-3 sm:pt-4 border-t-2 border-divider">
                      <button
                        type="submit"
                        disabled={isSaving}
                        className={`${BTN_PRIMARY} w-full sm:w-auto min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                      >
                        {isSaving ? "Saving changes..." : "Save Changes"}
                      </button>
                      <button
                        type="button"
                        onClick={handleCancelEdit}
                        disabled={isSaving}
                        className={`${BTN_GHOST} w-full sm:w-auto min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="space-y-4 sm:space-y-6 max-w-3xl w-full">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-6">
                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          Full Name
                        </span>
                        <p className="mt-1 break-words text-sm font-extrabold text-ink sm:text-base">
                          {formData.full_name || "Not set"}
                        </p>
                      </div>

                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          Username
                        </span>
                        <p className="mt-1 break-all font-mono text-sm font-bold text-ink sm:text-base">
                          @{user?.username || "N/A"}
                        </p>
                      </div>

                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          Email Address
                        </span>
                        <p className="mt-1 text-xs sm:text-base font-mono text-ink break-all">
                          {user?.email || "N/A"}
                        </p>
                      </div>

                      <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                        <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                          Location
                        </span>
                        <p className="mt-1 flex min-w-0 items-center gap-1.5 text-sm text-ink sm:text-base">
                          <MapPin className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-ink/40 flex-shrink-0" />
                          <span className="min-w-0 break-words">{formData.location || "Not set"}</span>
                        </p>
                      </div>
                    </div>

                    <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                      <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                        Bio
                      </span>
                      <p className="mt-1 text-xs sm:text-sm text-ink leading-relaxed break-words">
                        {formData.bio || "No bio added yet. Click 'Edit Details' to share your background."}
                      </p>
                    </div>

                    <div className="border border-divider p-3 sm:p-4 bg-paper/40">
                      <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                        Website & Links
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
                            <span className="min-w-0 break-all">{formData.website}</span>
                            <ExternalLink className="h-3 w-3 flex-shrink-0" />
                          </a>
                        ) : (
                          <span className="text-ink/60">No website provided</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: ROLE & PERSONA */}
            {activeTab === "persona" && (
              <div className="border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 space-y-6 sm:space-y-8 w-full max-w-full">
                <div>
                  <h3 className="text-lg sm:text-xl font-extrabold text-ink">Role & Persona Configuration</h3>
                  <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                    Your persona shapes your dashboard presets, terminology, and AI quiz generation defaults.
                  </p>
                </div>

                {/* Current Persona Summary Card */}
                <div className="border-2 border-brand/30 bg-brand-50/40 p-3.5 sm:p-5 w-full max-w-full">
                  <div className="flex flex-wrap items-center justify-between gap-2.5">
                    <div className="min-w-0 flex-1">
                      <span className="text-[10px] sm:text-xs font-extrabold uppercase tracking-widest text-brand-700">
                        Current Active Persona
                      </span>
                      <h4 className="mt-0.5 break-words text-xl font-black text-ink sm:mt-1 sm:text-2xl">
                        {personaLabel}
                      </h4>
                    </div>
                    <span className="inline-flex items-center gap-1 bg-brand px-2 sm:px-3 py-1 text-[10px] sm:text-xs font-extrabold uppercase tracking-wider text-paper flex-shrink-0">
                      <Check className="h-3 w-3 sm:h-3.5 sm:w-3.5" /> Active in Session
                    </span>
                  </div>

                  {definition && (
                    <div className="mt-3 sm:mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-4 border-t-2 border-brand/20 pt-3 sm:pt-4 text-xs">
                      <div className="break-words">
                        <span className="font-bold text-ink/60">Workflow Purpose:</span>
                        <p className="mt-0.5 font-medium text-ink">{definition.description}</p>
                      </div>
                      <div className="break-words">
                        <span className="font-bold text-ink/60">Default Topic:</span>
                        <p className="mt-0.5 font-medium text-ink">{definition.defaultTopic}</p>
                      </div>
                      <div className="break-words">
                        <span className="font-bold text-ink/60">Generation Preset:</span>
                        <p className="mt-0.5 font-medium text-ink">
                          {definition.generationDefaults.audienceType} · {definition.generationDefaults.difficultyLevel} difficulty
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Switch Persona Picker */}
                <div className="border-t-2 border-divider pt-4 sm:pt-6 w-full max-w-full">
                  <div className="mb-4 sm:mb-6">
                    <h4 className="text-base sm:text-lg font-extrabold text-ink">
                      Switch Your Role
                    </h4>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                      Select below to change your persona across Quiz Generator.
                    </p>
                  </div>
                  <PersonaPicker
                    heading="Select your target persona"
                    onPicked={() => {
                      toast.success("Persona updated successfully.");
                    }}
                  />
                </div>
              </div>
            )}

            {/* TAB 3: SUBSCRIPTION & BILLING */}
            {activeTab === "billing" && (
              <div className="border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 space-y-4 sm:space-y-6 w-full max-w-full">
                <div className="border-b-2 border-divider pb-3 sm:pb-4">
                  <h3 className="text-lg sm:text-xl font-extrabold text-ink">Subscription & Billing</h3>
                  <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                    Manage your current plan, invoice history, and billing credentials.
                  </p>
                </div>

                <div className="border-2 border-divider p-4 sm:p-6 bg-paper/30 w-full max-w-full">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-ink/60">
                        Current Tier
                      </span>
                      <h4 className="text-xl sm:text-2xl font-black text-ink mt-0.5">
                        {formatPlanLabel(billingPlan)} Plan
                      </h4>
                      <div className="mt-2 flex items-center gap-2">
                        <span
                          className={`inline-flex border px-2 sm:px-2.5 py-0.5 text-[11px] sm:text-xs font-extrabold uppercase tracking-wide ${subscriptionStatusClassName}`}
                        >
                          Status: {formatStatusLabel(billingStatus)}
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
                          {isOpeningPortal ? "Opening portal..." : "Manage Subscription"}
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => router.push("/#pricing")}
                          className={`${BTN_PRIMARY} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                        >
                          View Upgrade Plans
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => router.push("/billing_history")}
                        className={`${BTN_GHOST} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                      >
                        Billing History
                      </button>
                    </div>
                  </div>

                  <p className="mt-4 text-xs text-ink/70 border-t-2 border-divider pt-3 sm:pt-4 leading-relaxed">
                    {billingRenewalDate
                      ? `Your subscription is scheduled to renew on ${new Date(billingRenewalDate).toLocaleDateString()}.`
                      : billingPlan === "free"
                        ? "You are on the free starter plan. Upgrade anytime for unlimited generation and team features."
                        : "Renewal details will appear once confirmed by Stripe."}
                  </p>
                </div>
              </div>
            )}

            {/* TAB 4: SECURITY & ACCOUNT */}
            {activeTab === "security" && (
              <div className="border-2 border-divider bg-white p-3.5 sm:p-6 md:p-8 space-y-6 sm:space-y-8 w-full max-w-full">
                <div className="border-b-2 border-divider pb-3 sm:pb-4">
                  <h3 className="text-lg sm:text-xl font-extrabold text-ink">Security & Credentials</h3>
                  <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                    Manage password reset links, email address verification, and account removal.
                  </p>
                </div>

                {/* Password Reset */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 border-b-2 border-divider pb-4 sm:pb-6">
                  <div>
                    <h4 className="text-sm sm:text-base font-extrabold text-ink flex items-center gap-2">
                      <KeyRound className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-brand" /> Password & Login
                    </h4>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5">
                      Request a secure password reset link sent to your registered email.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRequestPasswordReset}
                    className={`${BTN_GHOST} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                  >
                    Reset Password
                  </button>
                </div>

                {/* Email Update */}
                <div className="border-b-2 border-divider pb-4 sm:pb-6 space-y-3 sm:space-y-4">
                  <div>
                    <h4 className="text-sm sm:text-base font-extrabold text-ink flex items-center gap-2">
                      <Mail className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-brand" /> Change Email Address
                    </h4>
                    <p className="text-[11px] sm:text-xs text-ink/60 mt-0.5 break-all">
                      Current address: <strong className="font-mono text-ink">{user?.email}</strong>
                    </p>
                  </div>

                  <div className="max-w-md space-y-3 w-full">
                    <input
                      type="email"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      placeholder="Enter new email address"
                      className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                    />
                    <button
                      type="button"
                      onClick={handleUpdateEmail}
                      className={`${BTN_PRIMARY} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                    >
                      Send Verification Code
                    </button>

                    {emailChangePending && (
                      <div className="mt-3 sm:mt-4 p-3 sm:p-4 border-2 border-brand/30 bg-brand-50/50 space-y-3">
                        <label className="block text-[11px] sm:text-xs font-bold uppercase tracking-wider text-brand-900">
                          Enter 6-Digit Verification Code
                        </label>
                        <input
                          type="text"
                          value={emailOtp}
                          onChange={(e) => setEmailOtp(e.target.value)}
                          placeholder="Verification code"
                          className="w-full border-2 border-divider px-3 py-2 text-xs sm:text-sm text-ink focus:border-brand focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={handleVerifyEmailChange}
                          className={`${BTN_PRIMARY} w-full sm:w-auto text-xs sm:text-sm min-h-[38px] sm:min-h-[44px]`}
                        >
                          Verify & Update Email
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Danger Zone */}
                <div className="border-2 border-rose-200 bg-rose-50/40 p-3.5 sm:p-5 w-full max-w-full">
                  <h4 className="text-sm sm:text-base font-extrabold text-rose-800 flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-rose-700" /> Danger Zone: Delete Account
                  </h4>
                  <p className="mt-1 text-[11px] sm:text-xs text-rose-700 leading-relaxed max-w-2xl">
                    Permanently delete your user account, generated quizzes, score records, and persona history.
                    This action cannot be undone.
                  </p>
                  <div className="mt-3 sm:mt-4">
                    <button
                      type="button"
                      onClick={() => setShowDeleteConfirm(true)}
                      className={`${BTN_BASE} border-2 border-rose-700 bg-rose-600 text-white hover:bg-rose-700 w-full sm:w-auto min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm px-3 py-2`}
                    >
                      <Trash2 className="mr-1.5 h-3.5 w-3.5 sm:h-4 sm:w-4" />
                      Delete Account
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
              <h3 className="text-lg sm:text-xl font-extrabold text-ink">Confirm Sign Out</h3>
              <p className="mt-2 text-xs sm:text-sm text-ink/70">
                Are you sure you want to end your current session?
              </p>
              <div className="mt-6 flex flex-col sm:flex-row gap-2 sm:gap-3">
                <button
                  type="button"
                  onClick={() => setShowLogoutConfirm(false)}
                  disabled={isLoggingOut}
                  className={`${BTN_GHOST} flex-1 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className={`${BTN_PRIMARY} flex-1 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  {isLoggingOut ? "Signing out..." : "Sign Out"}
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
                Permanently Delete Account?
              </h3>
              <p className="mt-2 text-xs sm:text-sm text-ink/70">
                This will delete all your quizzes, live results, and saved account data. This action is irreversible.
              </p>
              <div className="mt-6 flex flex-col sm:flex-row gap-2 sm:gap-3">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className={`${BTN_GHOST} flex-1 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  Keep Account
                </button>
                <button
                  type="button"
                  onClick={handleDeleteAccount}
                  className={`${BTN_BASE} flex-1 border-2 border-rose-700 bg-rose-600 text-white hover:bg-rose-700 min-h-[38px] sm:min-h-[44px] text-xs sm:text-sm`}
                >
                  Confirm Delete
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
