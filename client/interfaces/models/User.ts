export interface User {
  id: string;
  username: string;
  email: string;
  isVerified: boolean;
  full_name?: string;
  bio?: string;
  location?: string;
  website?: string;
  avatar_color?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface UpdateProfilePayload {
  full_name?: string;
  bio?: string;
  location?: string;
  website?: string;
  avatar_color?: string;
}

export interface UpdateProfileResponse {
  message: string;
  user: User;
}

export interface LoginResponse {
  message: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RefreshTokenPayload {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
}

export interface RegisterResponse {
  user: User;
  message?: string;
}

export interface LoginPayload {
  identifier: string; // email or username
  password: string;
}
