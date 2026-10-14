import { useTranslation } from "react-i18next";
import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { ROUTES } from "@shared/config/patterns/routes";
import { verifyLink } from "@features/auth/api/authApi";

const VerifyEmailPage: React.FC = () => {
  const { t: uiText } = useTranslation("ui");

  const router = useRouter();
  const { token } = router.query; // Récupère le token depuis l'URL
  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading",
  );
  const [message, setMessage] = useState("");

  useEffect(() => {
    const verifyEmailByToken = async (tokenValue: string) => {
      try {
        await verifyLink(tokenValue);
        setStatus("success");
        setMessage("Email verified successfully! Redirecting to login...");

        setTimeout(() => {
          router.push(ROUTES.LOGIN);
        }, 2000);
      } catch (err: any) {
        setStatus("error");
        setMessage(
          err.response?.data?.detail ||
            "Verification failed. The link may be expired.",
        );
      }
    };

    if (token && typeof token === "string") {
      verifyEmailByToken(token);
    }
  }, [router, token]);

  return (
    <div className="min-h-screen flex justify-center items-center bg-gray-100">
      <div className="bg-white rounded-2xl shadow-lg w-full max-w-md p-8 text-center">
        <h2 className="text-2xl font-semibold text-[#143E6F] font-serif mb-6">
          {uiText("m36575d819a4c6ced")}
        </h2>

        {status === "loading" && (
          <div>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#143E6F] mx-auto mb-4"></div>
            <p className="text-gray-600">{uiText("m7b3734fae0c5c888")}</p>
          </div>
        )}

        {status === "success" && (
          <div>
            <div className="text-green-500 text-5xl mb-4">✓</div>
            <p className="text-green-600 font-medium">{message}</p>
          </div>
        )}

        {status === "error" && (
          <div>
            <div className="text-red-500 text-5xl mb-4">✗</div>
            <p className="text-red-600 font-medium mb-6">{message}</p>
            <button
              onClick={() => router.push(ROUTES.LOGIN)}
              className="bg-[#143E6F] text-white px-6 py-2 rounded-md hover:bg-[#0f2f54]"
            >
              {uiText("m6dd273b16dd0bca7")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default VerifyEmailPage;
