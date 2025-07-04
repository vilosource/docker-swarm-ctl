import { useEffect, useState, useRef, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { useAuthStore } from '../store/authStore';

export interface LogMessage {
  type: 'log' | 'error' | 'ping';
  timestamp: string;
  data?: string;
  message?: string;
  container_id?: string;
}

export interface UseContainerLogsOptions {
  follow?: boolean;
  tail?: number;
  timestamps?: boolean;
  since?: string;
}

export function useContainerLogs(
  containerId: string | null,
  options: UseContainerLogsOptions = {}
) {
  const [logs, setLogs] = useState<string[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { token } = useAuthStore();
  
  const {
    follow = true,
    tail = 100,
    timestamps = true,
    since
  } = options;

  // Build WebSocket URL with query parameters
  const wsUrl = containerId && token
    ? `${import.meta.env.VITE_WS_URL}/containers/${containerId}/logs?token=${token}&follow=${follow}&tail=${tail}&timestamps=${timestamps}${since ? `&since=${since}` : ''}`
    : null;
  
  // Debug logging
  useEffect(() => {
    if (wsUrl) {
      console.log('WebSocket URL:', wsUrl);
      console.log('Container ID:', containerId);
      console.log('Token exists:', !!token);
    }
  }, [wsUrl, containerId, token]);

  const handleMessage = useCallback((message: LogMessage) => {
    console.log('WebSocket message:', message);
    if (message.type === 'log' && message.data) {
      setLogs(prev => [...prev, message.data]);
      setIsStreaming(true);
    } else if (message.type === 'error') {
      console.error('Log stream error:', message.message);
      setIsStreaming(false);
    }
    // Ignore ping messages
  }, []);

  const { isConnected, error, reconnect } = useWebSocket({
    url: wsUrl,
    onMessage: handleMessage,
    enabled: !!containerId && !!token,
  });

  // Clear logs when container changes
  useEffect(() => {
    setLogs([]);
    setIsStreaming(false);
  }, [containerId]);

  // Auto-scroll to bottom when new logs arrive
  const scrollToBottom = useCallback(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    if (isStreaming) {
      scrollToBottom();
    }
  }, [logs, isStreaming, scrollToBottom]);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  return {
    logs,
    isConnected,
    isStreaming,
    error,
    clearLogs,
    reconnect,
    scrollToBottom,
    logsEndRef,
  };
}