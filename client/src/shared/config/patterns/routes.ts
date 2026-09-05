export const ROUTES = {
  HOME: "/",
  LOGIN: "/auth/login",
  REGISTER: "/auth/register",
  VERIFY_EMAIL: "/auth/verify-email",
  VERIFY_EMAIL_NOTICE: "/auth/verify-email-notice",
  REQUEST_PASSWORD_RESET: "/auth/request-reset-password",
  RESET_PASSWORD: "/auth/reset-password",

  DASHBOARD: "/dashboard",
  PROFILE: "/profile",
  NOTIFICATIONS: "/notifications",
  ADMIN_NOTIFICATIONS: "/admin/notifications",

  TRAINING_RUNS: "/training-runs",
  ASSIGNED_TRAINING: "/assigned-training",
  TRAINING_ACCESS: "/training-access",

  trainingRun: (runId: string) => `/training-runs/${encodeURIComponent(runId)}`,
  trainingAccess: (accessCode: string) =>
    `/training-access/${encodeURIComponent(accessCode)}`,

  NOT_FOUND: "/404",
};
