import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import toast from 'react-hot-toast';
import { useAuth } from './AuthContext';
import { GameEvent, MarketUpdate, CombatUpdate } from '../types/game';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketContextType {
  socket: Socket | null;
  connectionStatus: ConnectionStatus;
  sendMessage: (type: string, data: any) => void;
  onGameEvent: (callback: (event: GameEvent) => void) => void;
  onMarketUpdate: (callback: (update: MarketUpdate) => void) => void;
  onCombatUpdate: (callback: (update: CombatUpdate) => void) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const { user } = useAuth();
  const [socket, setSocket] = useState<Socket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');

  const sendMessage = useCallback((type: string, data: any) => {
    if (socket && socket.connected) {
      socket.emit('message', { type, data });
    }
  }, [socket]);

  const onGameEvent = useCallback((callback: (event: GameEvent) => void) => {
    if (socket) {
      socket.on('game_event', callback);
      return () => socket.off('game_event', callback);
    }
  }, [socket]);

  const onMarketUpdate = useCallback((callback: (update: MarketUpdate) => void) => {
    if (socket) {
      socket.on('market_update', callback);
      return () => socket.off('market_update', callback);
    }
  }, [socket]);

  const onCombatUpdate = useCallback((callback: (update: CombatUpdate) => void) => {
    if (socket) {
      socket.on('combat_update', callback);
      return () => socket.off('combat_update', callback);
    }
  }, [socket]);

  useEffect(() => {
    if (user) {
      setConnectionStatus('connecting');
      
      // Create WebSocket connection
      const newSocket = io(`ws://localhost:8000/ws/${user.id}`, {
        transports: ['websocket'],
        auth: {
          token: localStorage.getItem('token'),
        },
      });

      // Connection event handlers
      newSocket.on('connect', () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
        toast.success('Connected to game server');
      });

      newSocket.on('disconnect', (reason) => {
        console.log('WebSocket disconnected:', reason);
        setConnectionStatus('disconnected');
        toast.error('Disconnected from game server');
      });

      newSocket.on('connect_error', (error) => {
        console.error('WebSocket connection error:', error);
        setConnectionStatus('error');
        toast.error('Failed to connect to game server');
      });

      // Game event handlers
      newSocket.on('game_state_update', (data) => {
        console.log('Game state update:', data);
      });

      newSocket.on('world_event', (data) => {
        console.log('World event:', data);
        toast(`🌍 ${data.title}`, {
          duration: 6000,
          style: {
            background: '#ff9800',
            color: '#000',
          },
        });
      });

      newSocket.on('travel_complete', (data) => {
        console.log('Travel complete:', data);
        toast.success(`Vehicle arrived at destination!`);
      });

      newSocket.on('mission_update', (data) => {
        console.log('Mission update:', data);
        if (data.status === 'completed') {
          toast.success(`Mission completed! +${data.reward_credits} credits`);
        } else if (data.status === 'failed') {
          toast.error(`Mission failed: ${data.reason}`);
        }
      });

      newSocket.on('combat_update', (data) => {
        console.log('Combat update:', data);
        if (data.winner_id === user.id) {
          toast.success('Combat victory!');
        } else {
          toast.error('Combat defeat!');
        }
      });

      newSocket.on('alliance_update', (data) => {
        console.log('Alliance update:', data);
        toast(`🤝 Alliance: ${data.message}`);
      });

      newSocket.on('notification', (data) => {
        console.log('Notification:', data);
        toast(data.message, {
          icon: data.type === 'success' ? '✅' : data.type === 'warning' ? '⚠️' : 'ℹ️',
        });
      });

      newSocket.on('pirate_encounter', (data) => {
        console.log('Pirate encounter:', data);
        toast.error('⚔️ Pirates spotted! Prepare for combat!', {
          duration: 8000,
        });
      });

      setSocket(newSocket);

      return () => {
        newSocket.close();
        setSocket(null);
        setConnectionStatus('disconnected');
      };
    } else {
      // User logged out, close connection
      if (socket) {
        socket.close();
        setSocket(null);
        setConnectionStatus('disconnected');
      }
    }
  }, [user]);

  // Ping server periodically to keep connection alive
  useEffect(() => {
    if (socket && connectionStatus === 'connected') {
      const pingInterval = setInterval(() => {
        sendMessage('ping', {});
      }, 30000); // Ping every 30 seconds

      return () => clearInterval(pingInterval);
    }
  }, [socket, connectionStatus, sendMessage]);

  const value = {
    socket,
    connectionStatus,
    sendMessage,
    onGameEvent,
    onMarketUpdate,
    onCombatUpdate,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
