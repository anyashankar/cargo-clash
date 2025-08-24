"""SQLAlchemy models for Cargo Clash game."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, 
    JSON, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class VehicleType(str, Enum):
    TRUCK = "truck"
    SHIP = "ship"
    PLANE = "plane"
    TRAIN = "train"


class CargoType(str, Enum):
    FOOD = "food"
    FUEL = "fuel"
    ELECTRONICS = "electronics"
    WEAPONS = "weapons"
    ARTIFACTS = "artifacts"
    MATERIALS = "materials"


class MissionStatus(str, Enum):
    AVAILABLE = "available"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class GameEventType(str, Enum):
    MARKET_SHIFT = "market_shift"
    WEATHER_CHANGE = "weather_change"
    PIRATE_ATTACK = "pirate_attack"
    FACTION_WAR = "faction_war"
    TRADE_ROUTE_BLOCKED = "trade_route_blocked"


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    cognito_id = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    credits = Column(Integer, default=10000)
    reputation = Column(Integer, default=0)
    faction_id = Column(Integer, ForeignKey("factions.id"), nullable=True)
    
    # Location and status
    current_location_id = Column(Integer, ForeignKey("locations.id"))
    is_online = Column(Boolean, default=False)
    last_active = Column(DateTime, default=func.now())
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    vehicles = relationship("Vehicle", back_populates="owner")
    missions = relationship("Mission", back_populates="player")
    faction = relationship("Faction", back_populates="members", foreign_keys=[faction_id])
    current_location = relationship("Location")
    combat_logs = relationship("CombatLog", back_populates="player")


class Faction(Base):
    __tablename__ = "factions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    leader_id = Column(Integer, ForeignKey("players.id"))
    territory_control = Column(JSON)  # Store controlled regions
    reputation = Column(Integer, default=0)
    treasury = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    members = relationship("Player", back_populates="faction", foreign_keys="Player.faction_id")
    leader = relationship("Player", foreign_keys=[leader_id], post_update=True)


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    location_type = Column(String(50))  # city, port, trade_hub, etc.
    x_coordinate = Column(Float, nullable=False)
    y_coordinate = Column(Float, nullable=False)
    region = Column(String(50))
    danger_level = Column(Integer, default=1)  # 1-10 scale
    
    # Economic data
    market_data = Column(JSON)  # Current prices for different cargo types
    population = Column(Integer, default=0)
    prosperity = Column(Integer, default=50)  # 0-100 scale
    
    # Control and status
    controlling_faction_id = Column(Integer, ForeignKey("factions.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    controlling_faction = relationship("Faction")
    missions_from = relationship("Mission", foreign_keys="Mission.origin_id")
    missions_to = relationship("Mission", foreign_keys="Mission.destination_id")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    name = Column(String(100), nullable=False)
    vehicle_type = Column(SQLEnum(VehicleType), nullable=False)
    
    # Stats
    speed = Column(Integer, default=50)
    cargo_capacity = Column(Integer, default=100)
    fuel_capacity = Column(Integer, default=100)
    current_fuel = Column(Integer, default=100)
    durability = Column(Integer, default=100)
    max_durability = Column(Integer, default=100)
    
    # Combat stats
    attack_power = Column(Integer, default=10)
    defense = Column(Integer, default=10)
    
    # Current status
    current_location_id = Column(Integer, ForeignKey("locations.id"))
    destination_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    is_traveling = Column(Boolean, default=False)
    travel_start_time = Column(DateTime, nullable=True)
    estimated_arrival = Column(DateTime, nullable=True)
    
    # Cargo
    current_cargo = Column(JSON)  # Store cargo items and quantities
    
    # Upgrades and customization
    upgrades = Column(JSON)  # Store installed upgrades
    special_abilities = Column(JSON)  # Store special abilities
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("Player", back_populates="vehicles")
    current_location = relationship("Location", foreign_keys=[current_location_id])
    destination = relationship("Location", foreign_keys=[destination_id])
    crew_members = relationship("CrewMember", back_populates="vehicle")


class CrewMember(Base):
    __tablename__ = "crew_members"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    name = Column(String(100), nullable=False)
    specialization = Column(String(50))  # combat, navigation, repair, etc.
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    
    # Stats
    combat_skill = Column(Integer, default=10)
    navigation_skill = Column(Integer, default=10)
    repair_skill = Column(Integer, default=10)
    
    # Status
    is_active = Column(Boolean, default=True)
    salary = Column(Integer, default=100)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    vehicle = relationship("Vehicle", back_populates="crew_members")


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    mission_type = Column(String(50))  # transport, combat, exploration, etc.
    
    # Locations
    origin_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    destination_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    
    # Cargo requirements
    required_cargo = Column(JSON)  # What needs to be transported
    cargo_value = Column(Integer, default=0)
    
    # Mission parameters
    difficulty = Column(Integer, default=1)  # 1-10 scale
    time_limit = Column(Integer, nullable=True)  # Minutes
    reward_credits = Column(Integer, default=1000)
    reward_experience = Column(Integer, default=100)
    penalty_credits = Column(Integer, default=0)
    
    # Status and assignment
    status = Column(SQLEnum(MissionStatus), default=MissionStatus.AVAILABLE)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    # Requirements
    min_level = Column(Integer, default=1)
    required_vehicle_type = Column(SQLEnum(VehicleType), nullable=True)
    required_reputation = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    origin = relationship("Location", foreign_keys=[origin_id])
    destination = relationship("Location", foreign_keys=[destination_id])
    player = relationship("Player", back_populates="missions")


class GameEvent(Base):
    __tablename__ = "game_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(SQLEnum(GameEventType), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Event data
    event_data = Column(JSON)  # Store event-specific data
    affected_locations = Column(JSON)  # List of affected location IDs
    affected_players = Column(JSON)  # List of affected player IDs
    
    # Timing
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    severity = Column(Integer, default=1)  # 1-10 scale
    
    created_at = Column(DateTime, default=func.now())


class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    cargo_type = Column(SQLEnum(CargoType), nullable=False)
    buy_price = Column(Integer, nullable=False)
    sell_price = Column(Integer, nullable=False)
    supply = Column(Integer, default=100)
    demand = Column(Integer, default=100)
    
    # Price history for trends
    price_history = Column(JSON)  # Store recent price changes
    
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    location = relationship("Location")
    
    # Ensure unique combination of location and cargo type
    __table_args__ = (UniqueConstraint('location_id', 'cargo_type'),)


class CombatLog(Base):
    __tablename__ = "combat_logs"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    opponent_type = Column(String(50))  # player, pirate, npc
    opponent_id = Column(Integer, nullable=True)  # Player ID if PvP
    
    # Combat details
    location_id = Column(Integer, ForeignKey("locations.id"))
    combat_type = Column(String(50))  # attack, defense, raid
    
    # Results
    winner_id = Column(Integer, nullable=True)
    damage_dealt = Column(Integer, default=0)
    damage_received = Column(Integer, default=0)
    cargo_lost = Column(JSON)  # What cargo was lost
    cargo_gained = Column(JSON)  # What cargo was gained
    credits_lost = Column(Integer, default=0)
    credits_gained = Column(Integer, default=0)
    
    # Combat data
    combat_data = Column(JSON)  # Detailed combat log
    
    created_at = Column(DateTime, default=func.now())

    # Relationships
    player = relationship("Player", back_populates="combat_logs")
    location = relationship("Location")


class Alliance(Base):
    __tablename__ = "alliances"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    leader_id = Column(Integer, ForeignKey("players.id"))
    
    # Alliance stats
    total_members = Column(Integer, default=0)
    total_reputation = Column(Integer, default=0)
    treasury = Column(Integer, default=0)
    
    # Settings
    is_recruiting = Column(Boolean, default=True)
    min_level_requirement = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    leader = relationship("Player", foreign_keys=[leader_id])


class AllianceMembership(Base):
    __tablename__ = "alliance_memberships"

    id = Column(Integer, primary_key=True, index=True)
    alliance_id = Column(Integer, ForeignKey("alliances.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    role = Column(String(50), default="member")  # leader, officer, member
    joined_at = Column(DateTime, default=func.now())
    
    # Ensure unique membership
    __table_args__ = (UniqueConstraint('alliance_id', 'player_id'),)

    # Relationships
    alliance = relationship("Alliance")
    player = relationship("Player")
