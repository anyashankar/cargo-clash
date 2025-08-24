// User and Authentication Types
export interface User {
  id: number;
  username: string;
  email: string;
  level: number;
  experience: number;
  credits: number;
  reputation: number;
  faction_id?: number;
  current_location_id?: number;
  is_online: boolean;
  last_active: string;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

// Vehicle Types
export enum VehicleType {
  TRUCK = 'truck',
  SHIP = 'ship',
  PLANE = 'plane',
  TRAIN = 'train',
}

export interface Vehicle {
  id: number;
  owner_id: number;
  name: string;
  vehicle_type: VehicleType;
  speed: number;
  cargo_capacity: number;
  fuel_capacity: number;
  current_fuel: number;
  durability: number;
  max_durability: number;
  attack_power: number;
  defense: number;
  current_location_id?: number;
  destination_id?: number;
  is_traveling: boolean;
  travel_start_time?: string;
  estimated_arrival?: string;
  current_cargo: Record<string, number>;
  upgrades: Record<string, any>;
  special_abilities: Record<string, any>;
  created_at: string;
}

export interface VehicleCreateRequest {
  name: string;
  vehicle_type: VehicleType;
}

// Location Types
export interface Location {
  id: number;
  name: string;
  location_type: string;
  x_coordinate: number;
  y_coordinate: number;
  region: string;
  danger_level: number;
  market_data: Record<string, any>;
  population: number;
  prosperity: number;
  controlling_faction_id?: number;
  is_active: boolean;
  created_at: string;
}

// Mission Types
export enum MissionStatus {
  AVAILABLE = 'available',
  ACCEPTED = 'accepted',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  EXPIRED = 'expired',
}

export interface Mission {
  id: number;
  title: string;
  description: string;
  mission_type: string;
  origin_id: number;
  destination_id: number;
  required_cargo: Record<string, number>;
  cargo_value: number;
  difficulty: number;
  time_limit?: number;
  reward_credits: number;
  reward_experience: number;
  penalty_credits: number;
  status: MissionStatus;
  player_id?: number;
  accepted_at?: string;
  completed_at?: string;
  deadline?: string;
  min_level: number;
  required_vehicle_type?: VehicleType;
  required_reputation: number;
  created_at: string;
}

// Market Types
export enum CargoType {
  FOOD = 'food',
  FUEL = 'fuel',
  ELECTRONICS = 'electronics',
  WEAPONS = 'weapons',
  ARTIFACTS = 'artifacts',
  MATERIALS = 'materials',
}

export interface MarketPrice {
  id: number;
  location_id: number;
  cargo_type: CargoType;
  buy_price: number;
  sell_price: number;
  supply: number;
  demand: number;
  price_history: Record<string, any>;
  last_updated: string;
}

export interface TradeRequest {
  location_id: number;
  cargo_type: string;
  quantity: number;
  vehicle_id: number;
}

// Combat Types
export interface CombatAction {
  action_type: string;
  target_id?: number;
  ability_name?: string;
}

export interface CombatResult {
  winner_id?: number;
  damage_dealt: number;
  damage_received: number;
  cargo_lost: Record<string, number>;
  cargo_gained: Record<string, number>;
  credits_lost: number;
  credits_gained: number;
  experience_gained: number;
}

// Alliance Types
export interface Alliance {
  id: number;
  name: string;
  description: string;
  leader_id: number;
  total_members: number;
  total_reputation: number;
  treasury: number;
  is_recruiting: boolean;
  min_level_requirement: number;
  created_at: string;
}

export interface AllianceCreateRequest {
  name: string;
  description: string;
  is_recruiting?: boolean;
  min_level_requirement?: number;
}

// Game Event Types
export enum GameEventType {
  MARKET_SHIFT = 'market_shift',
  WEATHER_CHANGE = 'weather_change',
  PIRATE_ATTACK = 'pirate_attack',
  FACTION_WAR = 'faction_war',
  TRADE_ROUTE_BLOCKED = 'trade_route_blocked',
}

export interface GameEvent {
  id: number;
  event_type: GameEventType;
  title: string;
  description: string;
  event_data: Record<string, any>;
  affected_locations: number[];
  affected_players: number[];
  start_time: string;
  end_time?: string;
  duration_minutes?: number;
  is_active: boolean;
  severity: number;
  created_at: string;
}

// WebSocket Message Types
export interface WebSocketMessage {
  type: string;
  data: Record<string, any>;
  timestamp: string;
}

export interface GameStateUpdate {
  player_positions: Record<number, { x: number; y: number }>;
  active_events: GameEvent[];
  market_updates: MarketPrice[];
  combat_updates: any[];
}

export interface MarketUpdate {
  location_id: number;
  market_data: Record<string, any>;
}

export interface CombatUpdate {
  participants: number[];
  result: CombatResult;
  location_id: number;
}

// Statistics Types
export interface PlayerStats {
  total_missions_completed: number;
  total_credits_earned: number;
  total_distance_traveled: number;
  total_cargo_delivered: number;
  combat_wins: number;
  combat_losses: number;
  reputation_rank: number;
}

export interface LeaderboardEntry {
  player_id: number;
  username: string;
  score: number;
  rank: number;
}

export interface Leaderboard {
  category: string;
  entries: LeaderboardEntry[];
  last_updated: string;
}

// Game State
export interface GameState {
  onlinePlayers: number;
  activeEvents: GameEvent[];
  serverTime: string;
}

// Travel Types
export interface TravelRequest {
  vehicle_id: number;
  destination_id: number;
}

export interface TravelResponse {
  success: boolean;
  message: string;
  estimated_arrival?: string;
  fuel_cost: number;
}

// API Response Types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Error Types
export interface ApiError {
  detail: string;
  status_code: number;
}

// Utility Types
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}
