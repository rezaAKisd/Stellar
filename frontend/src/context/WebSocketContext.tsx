import React, { createContext, useEffect, useState, ReactNode, useRef, useCallback } from 'react';
import { WebSocketClient } from '../api/websocket';
import { ProgressMessage } from '../types/websocket';
import { storage } from '../utils/storage';

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

  useEffect(() => {
    const token = storage.getToken();
    if (!token) {
      return;
    }

    // Create WebSocket client
    clientRef.current = new WebSocketClient(token);

    // Connect to WebSocket
    clientRef.current
      .connect()
      .then(() => {
        setIsConnected(true);
        console.log('WebSocket connected in context');
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
  }, []);

  const subscribe = useCallback(
    (projectId: string, callback: (message: ProgressMessage) => void): (() => void) => {
      if (!clientRef.current) {
        return () => {};
      }
      return clientRef.current.subscribe(projectId, callback);
    },
    []
  );

  const send = useCallback((data: string) => {
    if (clientRef.current) {
      clientRef.current.send(data);
    }
  }, []);

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
