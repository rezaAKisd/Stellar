import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';

const DEFAULT_API_ORIGIN =
  typeof window !== 'undefined' && window.location
    ? window.location.origin
    : 'http://localhost:8000';
const API_BASE_URL = process.env.REACT_APP_API_URL || DEFAULT_API_ORIGIN;
const API_PREFIX = process.env.REACT_APP_API_PREFIX || '/api/v1';

const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
  },
});

// Request interceptor: Add JWT token to all requests
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: Handle 401 (unauthorized) errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear token and redirect to sign in
      localStorage.removeItem('access_token');
      localStorage.removeItem('username');
      window.location.href = '/signin';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
