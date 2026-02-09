import React from "react";

interface SignInButtonProps {
  onOpen: () => void;
  className?: string;
}

const SignInButton: React.FC<SignInButtonProps> = ({
  onOpen,
  className = "",
}) => {
  return (
    <button
      type="button"
      onClick={onOpen}
      className={`
        text-base font-semibold text-[#0F2654] 
        border border-[#0F2654] bg-white 
        rounded-2xl px-6 py-2 hover:bg-gray-100 transition
        ${className}
      `}
    >
      Sign In
    </button>
  );
};

export default SignInButton;
