"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, EmailStr

from .models import VehicleType, CargoType, MissionStatus, GameEventType


# Authentication Schemas
class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Player Schemas
class PlayerBase(BaseModel):
    username: str
    email: EmailStr


class PlayerCreate(PlayerBase):
    cognito_id: str


class PlayerUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None


class PlayerResponse(PlayerBase):
    id: int
    level: int
    experience: int
    credits: int
    reputation: int
    faction_id: Optional[int] = None
    current_location_id: Optional[int] = None
    is_online: bool
    last_active: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Vehicle Schemas
class VehicleBase(BaseModel):
    name: str
    vehicle_type: VehicleType


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    name: Optional[str] = None


class VehicleResponse(VehicleBase):
    id: int
    owner_id: int
    speed: int
    cargo_capacity: int
    fuel_capacity: int
    current_fuel: int
    durability: int
    max_durability: int
    attack_power: int
    defense: int
    current_location_id: Optional[int] = None
    destination_id: Optional[int] = None
    is_traveling: bool
    travel_start_time: Optional[datetime] = None
    estimated_arrival: Optional[datetime] = None
    current_cargo: Dict[str, Any] = {}
    upgrades: Dict[str, Any] = {}
    special_abilities: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


# Location Schemas
class LocationBase(BaseModel):
    name: str
    location_type: str
    x_coordinate: float
    y_coordinate: float
    region: str


class LocationCreate(LocationBase):
    danger_level: int = 1
    population: int = 0
    prosperity: int = 50


class LocationResponse(LocationBase):
    id: int
    danger_level: int
    market_data: Dict[str, Any] = {}
    population: int
    prosperity: int
    controlling_faction_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Mission Schemas
class MissionBase(BaseModel):
    title: str
    description: str
    mission_type: str
    origin_id: int
    destination_id: int


class MissionCreate(MissionBase):
    required_cargo: Dict[str, Any] = {}
    cargo_value: int = 0
    difficulty: int = 1
    time_limit: Optional[int] = None
    reward_credits: int = 1000
    reward_experience: int = 100
    penalty_credits: int = 0
    min_level: int = 1
    required_vehicle_type: Optional[VehicleType] = None
    required_reputation: int = 0


class MissionUpdate(BaseModel):
    status: Optional[MissionStatus] = None


class MissionResponse(MissionBase):
    id: int
    required_cargo: Dict[str, Any]
    cargo_value: int
    difficulty: int
    time_limit: Optional[int] = None
    reward_credits: int
    reward_experience: int
    penalty_credits: int
    status: MissionStatus
    player_id: Optional[int] = None
    accepted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    min_level: int
    required_vehicle_type: Optional[VehicleType] = None
    required_reputation: int
    created_at: datetime

    class Config:
        from_attributes = True


# Game Event Schemas
class GameEventBase(BaseModel):
    event_type: GameEventType
    title: str
    description: str


class GameEventCreate(GameEventBase):
    event_data: Dict[str, Any] = {}
    affected_locations: List[int] = []
    affected_players: List[int] = []
    duration_minutes: Optional[int] = None
    severity: int = 1


class GameEventResponse(GameEventBase):
    id: int
    event_data: Dict[str, Any]
    affected_locations: List[int]
    affected_players: List[int]
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    is_active: bool
    severity: int
    created_at: datetime

    class Config:
        from_attributes = True


# Market Schemas
class MarketPriceBase(BaseModel):
    location_id: int
    cargo_type: CargoType
    buy_price: int
    sell_price: int


class MarketPriceCreate(MarketPriceBase):
    supply: int = 100
    demand: int = 100


class MarketPriceUpdate(BaseModel):
    buy_price: Optional[int] = None
    sell_price: Optional[int] = None
    supply: Optional[int] = None
    demand: Optional[int] = None


class MarketPriceResponse(MarketPriceBase):
    id: int
    supply: int
    demand: int
    price_history: Dict[str, Any] = {}
    last_updated: datetime

    class Config:
        from_attributes = True


# Combat Schemas
class CombatAction(BaseModel):
    action_type: str  # attack, defend, special_ability
    target_id: Optional[int] = None
    ability_name: Optional[str] = None


class CombatResult(BaseModel):
    winner_id: Optional[int]
    damage_dealt: int
    damage_received: int
    cargo_lost: Dict[str, Any] = {}
    cargo_gained: Dict[str, Any] = {}
    credits_lost: int = 0
    credits_gained: int = 0
    experience_gained: int = 0


# Travel Schemas
class TravelRequest(BaseModel):
    vehicle_id: int
    destination_id: int


class TravelResponse(BaseModel):
    success: bool
    message: str
    estimated_arrival: Optional[datetime] = None
    fuel_cost: int = 0


# Trade Schemas
class TradeOffer(BaseModel):
    cargo_type: CargoType
    quantity: int
    price_per_unit: int
    location_id: int


class TradeTransaction(BaseModel):
    buyer_id: int
    seller_id: int
    cargo_type: CargoType
    quantity: int
    total_price: int
    location_id: int


# Alliance Schemas
class AllianceBase(BaseModel):
    name: str
    description: str


class AllianceCreate(AllianceBase):
    is_recruiting: bool = True
    min_level_requirement: int = 1


class AllianceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_recruiting: Optional[bool] = None
    min_level_requirement: Optional[int] = None


class AllianceResponse(AllianceBase):
    id: int
    leader_id: int
    total_members: int
    total_reputation: int
    treasury: int
    is_recruiting: bool
    min_level_requirement: int
    created_at: datetime

    class Config:
        from_attributes = True


# WebSocket Schemas
class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any] = {}
    timestamp: datetime = datetime.utcnow()


class GameStateUpdate(BaseModel):
    player_positions: Dict[int, Dict[str, float]] = {}
    active_events: List[GameEventResponse] = []
    market_updates: List[MarketPriceResponse] = []
    combat_updates: List[Dict[str, Any]] = []


# Statistics Schemas
class PlayerStats(BaseModel):
    total_missions_completed: int
    total_credits_earned: int
    total_distance_traveled: float
    total_cargo_delivered: int
    combat_wins: int
    combat_losses: int
    reputation_rank: int


class LeaderboardEntry(BaseModel):
    player_id: int
    username: str
    score: int
    rank: int


class Leaderboard(BaseModel):
    category: str  # credits, reputation, missions, etc.
    entries: List[LeaderboardEntry]
    last_updated: datetime
