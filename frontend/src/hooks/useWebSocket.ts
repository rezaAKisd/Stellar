import { useEffect, useState } from 'react';
import { useWebSocketContext } from '../context/WebSocketContext';
import { ProgressMessage } from '../types/websocket';

/**
 * Custom hook to subscribe to WebSocket updates for a specific project
 *
 * Usage:
 * const { message, isConnected } = useWebSocket(projectId);
 *
 * useEffect(() => {
 *   if (message?.type === 'download_progress') {
 *     console.log('Progress:', message.progress);
 *   }
 * }, [message]);
 */
export const useWebSocket = (projectId: string | null) => {
  const { isConnected, subscribe } = useWebSocketContext();
  const [message, setMessage] = useState<ProgressMessage | null>(null);

  useEffect(() => {
    if (!projectId) {
      return;
    }

    const unsubscribe = subscribe(projectId, (msg: ProgressMessage) => {
      setMessage(msg);
    });

    return () => {
      unsubscribe();
    };
  }, [projectId, subscribe]);

  return { message, isConnected };
};

/**
 * Custom hook to get WebSocket connection status only
 *
 * Usage:
 * const isConnected = useWebSocketStatus();
 */
export const useWebSocketStatus = () => {
  const { isConnected } = useWebSocketContext();
  return isConnected;
};
