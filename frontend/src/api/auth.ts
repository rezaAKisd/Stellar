import apiClient from './client';
import {
  LoginRequest,
  LoginResponse,
  Verify2FARequest,
  Verify2FAResponse,
  UserResponse,
  RestoreSessionResponse,
  MessageResponse,
} from '../types/auth';

export const authApi = {
  /**
   * Login with username and password
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', data);
    return response.data;
  },

  /**
   * Verify 2FA code
   */
  verify2FA: async (data: Verify2FARequest): Promise<Verify2FAResponse> => {
    const response = await apiClient.post<Verify2FAResponse>('/auth/verify-2fa', data);
    return response.data;
  },

  /**
   * Logout current user
   */
  logout: async (): Promise<MessageResponse> => {
    const response = await apiClient.post<MessageResponse>('/auth/logout');
    return response.data;
  },

  /**
   * Get current user info
   */
  me: async (): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>('/auth/me');
    return response.data;
  },

  /**
   * Restore session from Instagram service
   */
  restoreSession: async (): Promise<RestoreSessionResponse> => {
    const response = await apiClient.post<RestoreSessionResponse>('/auth/restore-session');
    return response.data;
  },
};
