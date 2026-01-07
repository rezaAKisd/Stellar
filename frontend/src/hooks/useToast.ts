import { useToastContext } from '../context/ToastContext';

/**
 * Custom hook to access toast context
 *
 * Usage:
 * const { showToast } = useToast();
 * showToast('success', 'Operation completed!');
 */
export const useToast = () => {
  return useToastContext();
};
