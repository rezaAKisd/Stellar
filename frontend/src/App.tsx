import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { ProtectedRoute, PublicOnlyRoute } from './components/RouteGuards';
import { ToastViewport } from './components/ToastViewport';
import { SignInPage } from './pages/SignInPage';
import { TwoFactorPage } from './pages/TwoFactorPage';
import { DashboardPageNew } from './pages/DashboardPageNew';
import { UserDetailPage } from './pages/UserDetailPage';
import { DestinationDetailPage } from './pages/DestinationDetailPage';
import { HighlightDetailPage } from './pages/HighlightDetailPage';
import './App.css';
import './styles/modern.css';

// Create a client for React Query - No caching for API calls
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      retry: 1,
      staleTime: 0, // No caching - data is immediately stale
      gcTime: 0, // Don't cache data in memory (garbage collection time)
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <WebSocketProvider>
            <Router>
              <div className="App">
                <ToastViewport />
                <Routes>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />

                  <Route element={<PublicOnlyRoute />}>
                    <Route path="/signin" element={<SignInPage />} />
                    <Route path="/2fa" element={<TwoFactorPage />} />
                  </Route>

                  <Route element={<ProtectedRoute />}>
                    <Route path="/dashboard" element={<DashboardPageNew />} />
                    <Route path="/user/:username" element={<UserDetailPage />} />
                    <Route path="/destinations/:usernameId" element={<DestinationDetailPage />} />
                    <Route path="/highlights/:projectId" element={<HighlightDetailPage />} />
                  </Route>

                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </div>
            </Router>
          </WebSocketProvider>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
