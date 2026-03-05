import { useState } from "react";
import { useRouter } from "next/router";
import { ROUTES } from "../../constants/patterns/routes";
import RequestPasswordResetModal from "../../components/auth/RequestPasswordResetModal";

export default function RequestResetPasswordPage() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(true);
  const [email, setEmail] = useState("");

  const handleClose = () => {
    setIsOpen(false);
    router.push(ROUTES.LOGIN);
  };

  const handleSuccess = (submittedEmail: string) => {
    router.push({
      pathname: ROUTES.RESET_PASSWORD,
      query: { email: submittedEmail, mode: "otp" },
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <RequestPasswordResetModal
        isOpen={isOpen}
        onClose={handleClose}
        onRequestSuccess={handleSuccess}
      />
    </div>
  );
}
