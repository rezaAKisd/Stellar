import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { authApi } from '../api/auth';
import { storage } from '../utils/storage';

interface AuthContextType {
  user: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<{ success: boolean; needs2FA: boolean; error?: string }>;
  verify2FA: (username: string, password: string, code: string, trustDevice: boolean) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
  restoreSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Try to restore session on mount
    const initAuth = async () => {
      const token = storage.getToken();
      const username = storage.getUsername();

      if (token && username) {
        try {
          // Verify token is still valid
          const response = await authApi.me();
          if (response.is_authenticated) {
            setUser(response.username);
            setIsAuthenticated(true);
          } else {
            storage.clearAuth();
          }
        } catch (error) {
          // Token invalid, clear storage
          storage.clearAuth();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await authApi.login({ username, password });

      if (response.needs_2fa) {
        return { success: true, needs2FA: true };
      }

      // Login successful, save token
      storage.setToken(response.access_token);
      storage.setUsername(response.username);
      setUser(response.username);
      setIsAuthenticated(true);

      return { success: true, needs2FA: false };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed';
      return { success: false, needs2FA: false, error: errorMessage };
    }
  };

  const verify2FA = async (username: string, password: string, code: string, trustDevice: boolean) => {
    try {
      const response = await authApi.verify2FA({ username, password, code, trust_device: trustDevice });

      // 2FA successful, save token
      storage.setToken(response.access_token);
      storage.setUsername(response.username);
      setUser(response.username);
      setIsAuthenticated(true);

      return { success: true };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || '2FA verification failed';
      return { success: false, error: errorMessage };
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local state regardless
      storage.clearAuth();
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  const restoreSession = async (): Promise<boolean> => {
    try {
      const response = await authApi.restoreSession();
      if (response.is_authenticated) {
        // Session restored, generate new token
        const loginResponse = await authApi.login({
          username: response.username,
          password: '', // Empty password for session restoration
        });

        if (!loginResponse.needs_2fa) {
          storage.setToken(loginResponse.access_token);
          storage.setUsername(loginResponse.username);
          setUser(loginResponse.username);
          setIsAuthenticated(true);
          return true;
        }
      }
      return false;
    } catch (error) {
      console.error('Session restoration error:', error);
      return false;
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    verify2FA,
    logout,
    restoreSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuthContext = () => {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
};
