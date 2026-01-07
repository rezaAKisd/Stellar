/**
 * Local storage utilities for auth token and user data
 */

const TOKEN_KEY = 'access_token';
const USERNAME_KEY = 'username';

export const storage = {
  /**
   * Get access token from localStorage
   */
  getToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Set access token in localStorage
   */
  setToken: (token: string): void => {
    localStorage.setItem(TOKEN_KEY, token);
  },

  /**
   * Remove access token from localStorage
   */
  removeToken: (): void => {
    localStorage.removeItem(TOKEN_KEY);
  },

  /**
   * Get username from localStorage
   */
  getUsername: (): string | null => {
    return localStorage.getItem(USERNAME_KEY);
  },

  /**
   * Set username in localStorage
   */
  setUsername: (username: string): void => {
    localStorage.setItem(USERNAME_KEY, username);
  },

  /**
   * Remove username from localStorage
   */
  removeUsername: (): void => {
    localStorage.removeItem(USERNAME_KEY);
  },

  /**
   * Clear all auth data
   */
  clearAuth: (): void => {
    storage.removeToken();
    storage.removeUsername();
  },
};
