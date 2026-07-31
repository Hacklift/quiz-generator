import type { PersonaCategory, PersonaUserType } from "@shared/config/persona";

export interface User {
  id: string;
  username: string;
  email: string;
  is_verified: boolean;
  isVerified?: boolean;
  full_name?: string;
  bio?: string;
  location?: string;
  website?: string;
  avatar_color?: string;
  persona_category?: PersonaCategory | null;
  persona_user_type?: PersonaUserType | null;
  persona_set_at?: string | null;
  stripe_customer_id?: string | null;
  stripe_subscription_id?: string | null;
  subscription_plan?: string;
  subscription_status?: string;
  current_period_end?: string | null;
  created_at?: string;
  updated_at?: string;
  role?: "user" | "admin" | string;
  createdAt?: string;
  updatedAt?: string;
}

export interface UpdateProfilePayload {
  full_name?: string;
  bio?: string;
  location?: string;
  website?: string;
  avatar_color?: string;
  persona_category?: PersonaCategory;
  persona_user_type?: PersonaUserType;
}

export interface UpdateProfileResponse {
  message: string;
  user: User;
}

export interface LoginResponse {
  message: string;
  access_token: string;
  token_type: string;
  is_verified?: boolean;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterResponse {
  user: User;
  message?: string;
}

export interface LoginPayload {
  identifier: string; // email or username
  password: string;
}
