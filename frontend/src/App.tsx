import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { WebSocketProvider } from './context/WebSocketContext';
import './App.css';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: true,
      retry: 1,
      staleTime: 30000, // 30 seconds
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
                <Routes>
                  <Route path="/" element={<Navigate to="/signin" replace />} />
                  {/* Placeholder routes - will be implemented in Phase 6-7 */}
                  <Route path="/signin" element={<div>Sign In Page (Coming in Phase 6)</div>} />
                  <Route path="/2fa" element={<div>Two Factor Page (Coming in Phase 6)</div>} />
                  <Route path="/dashboard" element={<div>Dashboard Page (Coming in Phase 7)</div>} />
                  <Route path="/user/:username" element={<div>User Detail Page (Coming in Phase 7)</div>} />
                  <Route path="*" element={<Navigate to="/signin" replace />} />
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
