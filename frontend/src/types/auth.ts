export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  username: string;
  needs_2fa: boolean;
}

export interface Verify2FARequest {
  username: string;
  password: string;
  code: string;
  trust_device: boolean;
}

export interface Verify2FAResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export interface UserResponse {
  username: string;
  is_authenticated: boolean;
}

export interface MessageResponse {
  message: string;
}
