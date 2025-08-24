import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { gameService } from '../services/gameService';
import { GameState, Vehicle, Mission, Location } from '../types/game';
import { useAuth } from './AuthContext';

interface GameContextType {
  gameState: GameState | null;
  vehicles: Vehicle[];
  missions: Mission[];
  locations: Location[];
  loading: boolean;
  refreshGameState: () => Promise<void>;
  refreshVehicles: () => Promise<void>;
  refreshMissions: () => Promise<void>;
  refreshLocations: () => Promise<void>;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

interface GameProviderProps {
  children: ReactNode;
}

export const GameProvider: React.FC<GameProviderProps> = ({ children }) => {
  const { user } = useAuth();
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [missions, setMissions] = useState<Mission[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(false);

  const refreshGameState = async () => {
    if (!user) return;
    
    try {
      setLoading(true);
      // In a real implementation, this would fetch current game state
      const mockGameState: GameState = {
        onlinePlayers: 42,
        activeEvents: [],
        serverTime: new Date().toISOString(),
      };
      setGameState(mockGameState);
    } catch (error) {
      console.error('Failed to refresh game state:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshVehicles = async () => {
    if (!user) return;
    
    try {
      const vehicleData = await gameService.getVehicles();
      setVehicles(vehicleData);
    } catch (error) {
      console.error('Failed to refresh vehicles:', error);
    }
  };

  const refreshMissions = async () => {
    if (!user) return;
    
    try {
      const missionData = await gameService.getMissions();
      setMissions(missionData);
    } catch (error) {
      console.error('Failed to refresh missions:', error);
    }
  };

  const refreshLocations = async () => {
    if (!user) return;
    
    try {
      const locationData = await gameService.getLocations();
      setLocations(locationData);
    } catch (error) {
      console.error('Failed to refresh locations:', error);
    }
  };

  useEffect(() => {
    if (user) {
      refreshGameState();
      refreshVehicles();
      refreshMissions();
      refreshLocations();
    } else {
      // Clear data when user logs out
      setGameState(null);
      setVehicles([]);
      setMissions([]);
      setLocations([]);
    }
  }, [user]);

  const value = {
    gameState,
    vehicles,
    missions,
    locations,
    loading,
    refreshGameState,
    refreshVehicles,
    refreshMissions,
    refreshLocations,
  };

  return (
    <GameContext.Provider value={value}>
      {children}
    </GameContext.Provider>
  );
};

export const useGame = (): GameContextType => {
  const context = useContext(GameContext);
  if (context === undefined) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};
