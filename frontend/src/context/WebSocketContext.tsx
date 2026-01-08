import React, { createContext, useEffect, useState, ReactNode, useRef, useCallback } from 'react';
import { WebSocketClient } from '../api/websocket';
import { ProgressMessage } from '../types/websocket';
import { storage } from '../utils/storage';
import { useAuthContext } from './AuthContext';

interface WebSocketContextType {
  isConnected: boolean;
  subscribe: (projectId: string, callback: (message: ProgressMessage) => void) => () => void;
  send: (data: string) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const clientRef = useRef<WebSocketClient | null>(null);
  const { isAuthenticated } = useAuthContext();

  const ensureClient = useCallback((): WebSocketClient | null => {
    const token = storage.getToken();
    if (!token) {
      return null;
    }
    if (!clientRef.current) {
      clientRef.current = new WebSocketClient(token);
    }
    return clientRef.current;
  }, []);

  useEffect(() => {
    const token = storage.getToken();
    if (!isAuthenticated || !token) {
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }
      setIsConnected(false);
      return;
    }

    // Ensure client exists (subscribe effects may run before this effect)
    const client = ensureClient();
    if (!client) {
      setIsConnected(false);
      return;
    }

    client
      .connect()
      .then(() => {
        setIsConnected(true);
      })
      .catch((error) => {
        console.error('WebSocket connection error:', error);
        setIsConnected(false);
      });

    // Setup ping interval to keep connection alive
    const pingInterval = setInterval(() => {
      if (clientRef.current?.isConnected()) {
        clientRef.current.send('ping');
      }
    }, 30000); // Ping every 30 seconds

    // Cleanup on unmount
    return () => {
      clearInterval(pingInterval);
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }
      setIsConnected(false);
    };
  }, [ensureClient, isAuthenticated]);

  const subscribe = useCallback(
    (projectId: string, callback: (message: ProgressMessage) => void): (() => void) => {
      const client = ensureClient();
      if (!client) {
        return () => {};
      }
      return client.subscribe(projectId, callback);
    },
    [ensureClient]
  );

  const send = useCallback((data: string) => {
    const client = ensureClient();
    if (client) {
      client.send(data);
    }
  }, [ensureClient]);

  const value: WebSocketContextType = {
    isConnected,
    subscribe,
    send,
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
};

export const useWebSocketContext = () => {
  const context = React.useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
};
