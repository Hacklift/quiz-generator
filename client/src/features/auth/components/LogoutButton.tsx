import { useTranslation } from "react-i18next";
import { useLogout } from "@features/auth/hooks/useLogout";

export default function LogoutButton() {
  const { t: uiText } = useTranslation("ui");

  const { logout } = useLogout();

  return (
    <button
      onClick={logout}
      className="px-4 py-2 bg-red-600 text-white rounded-md"
    >
      {uiText("md0527e4b3d658351")}
    </button>
  );
}
