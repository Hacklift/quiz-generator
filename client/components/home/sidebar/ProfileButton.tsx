"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import SidebarButton from "./SidebarButton";

const ProfileButton = () => {
  const pathname = usePathname();
  const isActive = pathname === "/profile";

  return (
    <Link href="/profile">
      <SidebarButton label="My Profile" icon="👤" isActive={isActive} />
    </Link>
  );
};

export default ProfileButton;
