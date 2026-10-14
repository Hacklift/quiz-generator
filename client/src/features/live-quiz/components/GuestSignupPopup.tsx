import { useTranslation } from "react-i18next";
import Link from "next/link";
import React from "react";

interface GuestSignupPopupProps {
  isOpen: boolean;
  onClose: () => void;
}

const GuestSignupPopup: React.FC<GuestSignupPopupProps> = ({
  isOpen,
  onClose,
}) => {
  const { t: uiText } = useTranslation("ui");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
      <div className="w-full max-w-md rounded-md bg-white p-6 shadow-xl">
        <h2 className="text-xl font-bold text-[#0F2654]">
          {uiText("m0b668f7f02516046")}
        </h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          {uiText("m8dd7a54dbfa8b2c0")}
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/auth/register"
            className="rounded-md bg-[#0a3264] px-4 py-2 text-center text-sm font-semibold text-white hover:bg-[#082952]"
          >
            {uiText("m0dffe234b44793b6")}
          </Link>
          <Link
            href="/auth/login"
            className="rounded-md border border-slate-300 px-4 py-2 text-center text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            {uiText("m9d6322c1f4d9d3f3")}
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          >
            {uiText("m166b26ab559bf68d")}
          </button>
        </div>
      </div>
    </div>
  );
};

export default GuestSignupPopup;
