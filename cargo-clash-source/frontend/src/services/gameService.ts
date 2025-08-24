import api from './authService';
import {
  Vehicle,
  VehicleCreateRequest,
  Mission,
  Location,
  MarketPrice,
  TradeRequest,
  Alliance,
  AllianceCreateRequest,
  PlayerStats,
  Leaderboard,
  TravelRequest,
  TravelResponse,
  CombatAction,
  CombatResult,
} from '../types/game';

export const gameService = {
  // Vehicle endpoints
  async getVehicles(): Promise<Vehicle[]> {
    try {
      const response = await api.get<Vehicle[]>('/vehicles');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get vehicles');
    }
  },

  async createVehicle(data: VehicleCreateRequest): Promise<Vehicle> {
    try {
      const response = await api.post<Vehicle>('/vehicles', data);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to create vehicle');
    }
  },

  async getVehicle(id: number): Promise<Vehicle> {
    try {
      const response = await api.get<Vehicle>(`/vehicles/${id}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get vehicle');
    }
  },

  async startTravel(vehicleId: number, destinationId: number): Promise<TravelResponse> {
    try {
      const response = await api.post<TravelResponse>(`/vehicles/${vehicleId}/travel`, {
        vehicle_id: vehicleId,
        destination_id: destinationId,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to start travel');
    }
  },

  async refuelVehicle(vehicleId: number): Promise<any> {
    try {
      const response = await api.post(`/vehicles/${vehicleId}/refuel`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to refuel vehicle');
    }
  },

  async repairVehicle(vehicleId: number): Promise<any> {
    try {
      const response = await api.post(`/vehicles/${vehicleId}/repair`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to repair vehicle');
    }
  },

  // Mission endpoints
  async getMissions(params?: {
    location_id?: number;
    mission_type?: string;
    min_reward?: number;
    max_difficulty?: number;
  }): Promise<Mission[]> {
    try {
      const response = await api.get<Mission[]>('/missions', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get missions');
    }
  },

  async getMyMissions(statusFilter?: string): Promise<Mission[]> {
    try {
      const response = await api.get<Mission[]>('/missions/my', {
        params: statusFilter ? { status_filter: statusFilter } : undefined,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get my missions');
    }
  },

  async getMission(id: number): Promise<Mission> {
    try {
      const response = await api.get<Mission>(`/missions/${id}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get mission');
    }
  },

  async acceptMission(missionId: number, vehicleId: number): Promise<Mission> {
    try {
      const response = await api.post<Mission>(`/missions/${missionId}/accept`, {
        vehicle_id: vehicleId,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to accept mission');
    }
  },

  async startMission(missionId: number): Promise<Mission> {
    try {
      const response = await api.post<Mission>(`/missions/${missionId}/start`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to start mission');
    }
  },

  async completeMission(missionId: number): Promise<Mission> {
    try {
      const response = await api.post<Mission>(`/missions/${missionId}/complete`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to complete mission');
    }
  },

  async abandonMission(missionId: number): Promise<Mission> {
    try {
      const response = await api.post<Mission>(`/missions/${missionId}/abandon`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to abandon mission');
    }
  },

  // Location endpoints
  async getLocations(params?: {
    region?: string;
    location_type?: string;
  }): Promise<Location[]> {
    try {
      const response = await api.get<Location[]>('/locations', { params });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get locations');
    }
  },

  async getLocation(id: number): Promise<Location> {
    try {
      const response = await api.get<Location>(`/locations/${id}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get location');
    }
  },

  async getNearbyLocations(locationId: number, radius: number = 100): Promise<Location[]> {
    try {
      const response = await api.get<Location[]>(`/locations/${locationId}/nearby`, {
        params: { radius },
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get nearby locations');
    }
  },

  // Market endpoints
  async getMarketPrices(locationId?: number, cargoType?: string): Promise<MarketPrice[]> {
    try {
      const response = await api.get<MarketPrice[]>('/market/prices', {
        params: { location_id: locationId, cargo_type: cargoType },
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get market prices');
    }
  },

  async getLocationPrices(locationId: number): Promise<MarketPrice[]> {
    try {
      const response = await api.get<MarketPrice[]>(`/market/prices/${locationId}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get location prices');
    }
  },

  async buyCargo(data: TradeRequest): Promise<any> {
    try {
      const response = await api.post('/market/buy', data);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to buy cargo');
    }
  },

  async sellCargo(data: TradeRequest): Promise<any> {
    try {
      const response = await api.post('/market/sell', data);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to sell cargo');
    }
  },

  async getMarketTrends(locationId: number, cargoType?: string): Promise<any> {
    try {
      const response = await api.get(`/market/trends/${locationId}`, {
        params: cargoType ? { cargo_type: cargoType } : undefined,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get market trends');
    }
  },

  async getArbitrageOpportunities(cargoType: string, maxDistance?: number): Promise<any> {
    try {
      const response = await api.get('/market/arbitrage', {
        params: { cargo_type: cargoType, max_distance: maxDistance },
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get arbitrage opportunities');
    }
  },

  // Combat endpoints
  async attackPlayer(targetPlayerId: number, vehicleId: number, action: CombatAction): Promise<CombatResult> {
    try {
      const response = await api.post<CombatResult>(`/combat/attack/${targetPlayerId}`, action, {
        params: { attacker_vehicle_id: vehicleId },
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to attack player');
    }
  },

  async handlePirateEncounter(vehicleId: number, action: CombatAction): Promise<CombatResult> {
    try {
      const response = await api.post<CombatResult>(`/combat/pirate-encounter/${vehicleId}`, action);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to handle pirate encounter');
    }
  },

  async getCombatHistory(skip?: number, limit?: number): Promise<any[]> {
    try {
      const response = await api.get<any[]>('/combat/history', {
        params: { skip, limit },
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get combat history');
    }
  },

  async getCombatStats(): Promise<any> {
    try {
      const response = await api.get('/combat/stats');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get combat stats');
    }
  },

  // Alliance endpoints
  async getAlliances(recruitingOnly?: boolean): Promise<Alliance[]> {
    try {
      const response = await api.get<Alliance[]>('/alliances', {
        params: recruitingOnly ? { recruiting_only: true } : undefined,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get alliances');
    }
  },

  async createAlliance(data: AllianceCreateRequest): Promise<Alliance> {
    try {
      const response = await api.post<Alliance>('/alliances', data);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to create alliance');
    }
  },

  async getAlliance(id: number): Promise<Alliance> {
    try {
      const response = await api.get<Alliance>(`/alliances/${id}`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get alliance');
    }
  },

  async joinAlliance(allianceId: number): Promise<any> {
    try {
      const response = await api.post(`/alliances/${allianceId}/join`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to join alliance');
    }
  },

  async leaveAlliance(allianceId: number): Promise<any> {
    try {
      const response = await api.post(`/alliances/${allianceId}/leave`);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to leave alliance');
    }
  },

  async getMyAlliance(): Promise<Alliance | null> {
    try {
      const response = await api.get<Alliance>('/alliances/my/alliance');
      return response.data;
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null; // No alliance
      }
      throw new Error(error.response?.data?.detail || 'Failed to get my alliance');
    }
  },

  // Player stats and leaderboard
  async getMyStats(): Promise<PlayerStats> {
    try {
      const response = await api.get<PlayerStats>('/players/me/stats');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get player stats');
    }
  },

  async getLeaderboard(category: string, limit?: number): Promise<Leaderboard> {
    try {
      const response = await api.get<Leaderboard>(`/players/leaderboard/${category}`, {
        params: limit ? { limit } : undefined,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get leaderboard');
    }
  },
};
