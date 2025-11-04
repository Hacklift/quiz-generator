"use client";

import React from "react";
import Link from "next/link";
import SidebarButton from "./SidebarButton";

const ProfileButton = () => {
  return (
    <Link href="/profile">
      <SidebarButton label="My Profile" icon="👤" onClick={() => {}} />
    </Link>
  );
};

export default ProfileButton;
