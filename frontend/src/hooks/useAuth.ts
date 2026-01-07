import { useAuthContext } from '../context/AuthContext';

/**
 * Custom hook to access authentication context
 *
 * Usage:
 * const { user, isAuthenticated, login, logout } = useAuth();
 */
export const useAuth = () => {
  return useAuthContext();
};
