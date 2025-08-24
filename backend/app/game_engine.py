"""Game engine for handling real-time game logic and events."""

import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .database import AsyncSessionLocal
from .models import (
    Player, Vehicle, Mission, Location, GameEvent, MarketPrice, 
    GameEventType, MissionStatus, CargoType
)
from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)


class GameEngine:
    """Core game engine for handling real-time events and updates."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.is_running = False
        self.tick_rate = 10  # Updates per second
        self.last_market_update = datetime.utcnow()
        self.last_event_check = datetime.utcnow()
        self.active_events: Dict[int, GameEvent] = {}
        
        # Game state tracking
        self.player_positions: Dict[int, Dict[str, float]] = {}
        self.vehicle_travels: Dict[int, Dict[str, Any]] = {}
        
    async def start(self):
        """Start the game engine."""
        self.is_running = True
        logger.info("Game engine started")
        
        # Start main game loop
        await self._game_loop()
    
    async def stop(self):
        """Stop the game engine."""
        self.is_running = False
        logger.info("Game engine stopped")
    
    async def _game_loop(self):
        """Main game loop."""
        while self.is_running:
            try:
                await self._process_game_tick()
                await asyncio.sleep(1.0 / self.tick_rate)
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_game_tick(self):
        """Process a single game tick."""
        async with AsyncSessionLocal() as db:
            # Update vehicle travels
            await self._update_vehicle_travels(db)
            
            # Process market fluctuations
            await self._process_market_updates(db)
            
            # Check for random events
            await self._check_random_events(db)
            
            # Process active events
            await self._process_active_events(db)
            
            # Update mission deadlines
            await self._check_mission_deadlines(db)
            
            # Send periodic updates to connected players
            await self._send_periodic_updates(db)
    
    async def _update_vehicle_travels(self, db: AsyncSession):
        """Update vehicles that are currently traveling."""
        current_time = datetime.utcnow()
        
        # Get all traveling vehicles
        result = await db.execute(
            select(Vehicle)
            .options(
                selectinload(Vehicle.owner),
                selectinload(Vehicle.current_location),
                selectinload(Vehicle.destination)
            )
            .where(
                Vehicle.is_traveling == True,
                Vehicle.estimated_arrival <= current_time
            )
        )
        vehicles = result.scalars().all()
        
        for vehicle in vehicles:
            # Vehicle has arrived at destination
            vehicle.is_traveling = False
            vehicle.current_location_id = vehicle.destination_id
            vehicle.destination_id = None
            vehicle.travel_start_time = None
            vehicle.estimated_arrival = None
            
            # Update player location
            if vehicle.owner:
                vehicle.owner.current_location_id = vehicle.current_location_id
                
                # Update WebSocket manager
                self.websocket_manager.update_player_location(
                    vehicle.owner.id, 
                    vehicle.current_location_id
                )
                
                # Notify player of arrival
                await self.websocket_manager.send_personal_message(
                    vehicle.owner.id,
                    {
                        "type": "travel_complete",
                        "data": {
                            "vehicle_id": vehicle.id,
                            "location_id": vehicle.current_location_id,
                            "location_name": vehicle.current_location.name if vehicle.current_location else "Unknown"
                        }
                    }
                )
                
                # Check for random encounters
                await self._check_travel_encounters(vehicle, db)
        
        if vehicles:
            await db.commit()
    
    async def _check_travel_encounters(self, vehicle: Vehicle, db: AsyncSession):
        """Check for random encounters during travel."""
        if not vehicle.current_location:
            return
        
        danger_level = vehicle.current_location.danger_level
        encounter_chance = danger_level * 0.05  # 5% per danger level
        
        if random.random() < encounter_chance:
            # Random pirate encounter
            await self.websocket_manager.send_personal_message(
                vehicle.owner.id,
                {
                    "type": "pirate_encounter",
                    "data": {
                        "vehicle_id": vehicle.id,
                        "location_id": vehicle.current_location_id,
                        "danger_level": danger_level,
                        "message": "Pirates spotted! Prepare for combat!"
                    }
                }
            )
    
    async def _process_market_updates(self, db: AsyncSession):
        """Process market price fluctuations."""
        current_time = datetime.utcnow()
        
        # Update market prices every 5 minutes
        if (current_time - self.last_market_update).total_seconds() < 300:
            return
        
        self.last_market_update = current_time
        
        # Get all market prices
        result = await db.execute(
            select(MarketPrice).options(selectinload(MarketPrice.location))
        )
        market_prices = result.scalars().all()
        
        updated_locations = set()
        
        for price in market_prices:
            # Simulate supply and demand changes
            supply_change = random.randint(-10, 10)
            demand_change = random.randint(-10, 10)
            
            price.supply = max(0, price.supply + supply_change)
            price.demand = max(0, price.demand + demand_change)
            
            # Adjust prices based on supply and demand
            supply_demand_ratio = price.supply / max(price.demand, 1)
            
            if supply_demand_ratio > 1.5:
                # Oversupply - prices drop
                price.buy_price = max(1, int(price.buy_price * 0.95))
                price.sell_price = max(1, int(price.sell_price * 0.95))
            elif supply_demand_ratio < 0.7:
                # High demand - prices rise
                price.buy_price = int(price.buy_price * 1.05)
                price.sell_price = int(price.sell_price * 1.05)
            
            # Update price history
            if not price.price_history:
                price.price_history = {}
            
            price.price_history[current_time.isoformat()] = {
                "buy_price": price.buy_price,
                "sell_price": price.sell_price,
                "supply": price.supply,
                "demand": price.demand
            }
            
            # Keep only last 24 hours of history
            cutoff_time = current_time - timedelta(hours=24)
            price.price_history = {
                timestamp: data
                for timestamp, data in price.price_history.items()
                if datetime.fromisoformat(timestamp) > cutoff_time
            }
            
            updated_locations.add(price.location_id)
        
        await db.commit()
        
        # Notify players at updated locations
        for location_id in updated_locations:
            result = await db.execute(
                select(MarketPrice)
                .where(MarketPrice.location_id == location_id)
            )
            location_prices = result.scalars().all()
            
            market_data = {}
            for price in location_prices:
                market_data[price.cargo_type.value] = {
                    "buy_price": price.buy_price,
                    "sell_price": price.sell_price,
                    "supply": price.supply,
                    "demand": price.demand
                }
            
            await self.websocket_manager.send_market_update(location_id, market_data)
    
    async def _check_random_events(self, db: AsyncSession):
        """Check for and trigger random world events."""
        current_time = datetime.utcnow()
        
        # Check for events every 10 minutes
        if (current_time - self.last_event_check).total_seconds() < 600:
            return
        
        self.last_event_check = current_time
        
        # 10% chance of a random event
        if random.random() < 0.1:
            await self._trigger_random_event(db)
    
    async def _trigger_random_event(self, db: AsyncSession):
        """Trigger a random world event."""
        event_types = [
            GameEventType.MARKET_SHIFT,
            GameEventType.WEATHER_CHANGE,
            GameEventType.PIRATE_ATTACK,
            GameEventType.TRADE_ROUTE_BLOCKED
        ]
        
        event_type = random.choice(event_types)
        
        # Get random locations for the event
        result = await db.execute(
            select(Location).where(Location.is_active == True).limit(10)
        )
        locations = result.scalars().all()
        
        if not locations:
            return
        
        affected_locations = random.sample(locations, min(3, len(locations)))
        affected_location_ids = [loc.id for loc in affected_locations]
        
        # Create event based on type
        if event_type == GameEventType.MARKET_SHIFT:
            event = await self._create_market_shift_event(affected_location_ids, db)
        elif event_type == GameEventType.WEATHER_CHANGE:
            event = await self._create_weather_event(affected_location_ids, db)
        elif event_type == GameEventType.PIRATE_ATTACK:
            event = await self._create_pirate_event(affected_location_ids, db)
        elif event_type == GameEventType.TRADE_ROUTE_BLOCKED:
            event = await self._create_trade_route_event(affected_location_ids, db)
        
        if event:
            self.active_events[event.id] = event
            await db.commit()
            
            # Notify affected players
            await self.websocket_manager.send_world_event(
                {
                    "event_id": event.id,
                    "event_type": event.event_type.value,
                    "title": event.title,
                    "description": event.description,
                    "severity": event.severity,
                    "duration_minutes": event.duration_minutes,
                    "affected_locations": affected_location_ids
                },
                affected_location_ids
            )
    
    async def _create_market_shift_event(self, location_ids: List[int], db: AsyncSession) -> GameEvent:
        """Create a market shift event."""
        cargo_type = random.choice(list(CargoType))
        shift_direction = random.choice(["surge", "crash"])
        
        event = GameEvent(
            event_type=GameEventType.MARKET_SHIFT,
            title=f"{cargo_type.value.title()} Market {shift_direction.title()}",
            description=f"A sudden {shift_direction} in {cargo_type.value} prices affects multiple markets!",
            event_data={
                "cargo_type": cargo_type.value,
                "shift_direction": shift_direction,
                "price_multiplier": 1.5 if shift_direction == "surge" else 0.7
            },
            affected_locations=location_ids,
            duration_minutes=60,
            severity=random.randint(3, 7)
        )
        
        db.add(event)
        await db.flush()
        
        # Apply market effects
        result = await db.execute(
            select(MarketPrice).where(
                MarketPrice.location_id.in_(location_ids),
                MarketPrice.cargo_type == cargo_type
            )
        )
        prices = result.scalars().all()
        
        multiplier = event.event_data["price_multiplier"]
        for price in prices:
            price.buy_price = int(price.buy_price * multiplier)
            price.sell_price = int(price.sell_price * multiplier)
        
        return event
    
    async def _create_weather_event(self, location_ids: List[int], db: AsyncSession) -> GameEvent:
        """Create a weather event."""
        weather_types = ["storm", "fog", "hurricane", "blizzard"]
        weather_type = random.choice(weather_types)
        
        event = GameEvent(
            event_type=GameEventType.WEATHER_CHANGE,
            title=f"Severe {weather_type.title()}",
            description=f"A {weather_type} is affecting travel and trade in the region!",
            event_data={
                "weather_type": weather_type,
                "travel_delay_multiplier": 1.5,
                "fuel_cost_multiplier": 1.3
            },
            affected_locations=location_ids,
            duration_minutes=45,
            severity=random.randint(2, 6)
        )
        
        db.add(event)
        return event
    
    async def _create_pirate_event(self, location_ids: List[int], db: AsyncSession) -> GameEvent:
        """Create a pirate attack event."""
        event = GameEvent(
            event_type=GameEventType.PIRATE_ATTACK,
            title="Pirate Fleet Spotted",
            description="A large pirate fleet has been spotted in the area! Exercise extreme caution!",
            event_data={
                "pirate_strength_multiplier": 1.4,
                "encounter_chance_multiplier": 2.0
            },
            affected_locations=location_ids,
            duration_minutes=90,
            severity=random.randint(5, 9)
        )
        
        db.add(event)
        return event
    
    async def _create_trade_route_event(self, location_ids: List[int], db: AsyncSession) -> GameEvent:
        """Create a trade route blockage event."""
        event = GameEvent(
            event_type=GameEventType.TRADE_ROUTE_BLOCKED,
            title="Trade Route Disruption",
            description="Major trade routes have been disrupted, affecting cargo movement!",
            event_data={
                "travel_cost_multiplier": 1.8,
                "mission_reward_multiplier": 1.3
            },
            affected_locations=location_ids,
            duration_minutes=120,
            severity=random.randint(4, 7)
        )
        
        db.add(event)
        return event
    
    async def _process_active_events(self, db: AsyncSession):
        """Process and clean up active events."""
        current_time = datetime.utcnow()
        expired_events = []
        
        for event_id, event in self.active_events.items():
            if event.end_time and current_time > event.end_time:
                expired_events.append(event_id)
            elif event.duration_minutes:
                event_end = event.start_time + timedelta(minutes=event.duration_minutes)
                if current_time > event_end:
                    expired_events.append(event_id)
        
        # Remove expired events
        for event_id in expired_events:
            event = self.active_events[event_id]
            event.is_active = False
            event.end_time = current_time
            
            del self.active_events[event_id]
            
            # Notify players that event has ended
            await self.websocket_manager.send_world_event(
                {
                    "event_id": event.id,
                    "event_type": "event_ended",
                    "title": f"{event.title} - Ended",
                    "description": f"The {event.title.lower()} has ended.",
                    "affected_locations": event.affected_locations
                },
                event.affected_locations
            )
        
        if expired_events:
            await db.commit()
    
    async def _check_mission_deadlines(self, db: AsyncSession):
        """Check for expired missions."""
        current_time = datetime.utcnow()
        
        result = await db.execute(
            select(Mission)
            .options(selectinload(Mission.player))
            .where(
                Mission.status.in_([MissionStatus.ACCEPTED, MissionStatus.IN_PROGRESS]),
                Mission.deadline <= current_time
            )
        )
        expired_missions = result.scalars().all()
        
        for mission in expired_missions:
            mission.status = MissionStatus.FAILED
            
            if mission.player:
                # Apply penalty
                penalty = mission.penalty_credits or (mission.reward_credits // 4)
                mission.player.credits = max(0, mission.player.credits - penalty)
                mission.player.reputation = max(0, mission.player.reputation - 2)
                
                # Notify player
                await self.websocket_manager.send_mission_update(
                    mission.player.id,
                    {
                        "mission_id": mission.id,
                        "status": "failed",
                        "reason": "deadline_expired",
                        "penalty": penalty,
                        "new_credits": mission.player.credits,
                        "new_reputation": mission.player.reputation
                    }
                )
        
        if expired_missions:
            await db.commit()
    
    async def _send_periodic_updates(self, db: AsyncSession):
        """Send periodic game state updates to connected players."""
        # Send updates every 5 seconds
        if hasattr(self, '_last_periodic_update'):
            if (datetime.utcnow() - self._last_periodic_update).total_seconds() < 5:
                return
        
        self._last_periodic_update = datetime.utcnow()
        
        # Get basic game state
        connected_players = self.websocket_manager.get_connected_players()
        
        if not connected_players:
            return
        
        # Send connection stats to each player
        stats = self.websocket_manager.get_connection_stats()
        
        for player_id in connected_players:
            await self.websocket_manager.send_game_state_update(
                player_id,
                {
                    "online_players": stats["total_connections"],
                    "active_events": len(self.active_events),
                    "server_time": datetime.utcnow().isoformat()
                }
            )
    
    async def process_player_action(self, player_id: int, action_data: Dict[str, Any]):
        """Process a player action received via WebSocket."""
        action_type = action_data.get("type")
        
        if action_type == "ping":
            await self.websocket_manager.send_personal_message(
                player_id,
                {
                    "type": "pong",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                }
            )
        
        elif action_type == "get_game_state":
            async with AsyncSessionLocal() as db:
                await self._send_full_game_state(player_id, db)
        
        elif action_type == "update_location":
            location_id = action_data.get("location_id")
            if location_id:
                self.websocket_manager.update_player_location(player_id, location_id)
        
        # Add more action handlers as needed
    
    async def _send_full_game_state(self, player_id: int, db: AsyncSession):
        """Send full game state to a player."""
        # Get player data
        result = await db.execute(
            select(Player)
            .options(
                selectinload(Player.vehicles),
                selectinload(Player.current_location)
            )
            .where(Player.id == player_id)
        )
        player = result.scalar_one_or_none()
        
        if not player:
            return
        
        # Get active events
        active_events = [
            {
                "id": event.id,
                "type": event.event_type.value,
                "title": event.title,
                "description": event.description,
                "severity": event.severity,
                "affected_locations": event.affected_locations
            }
            for event in self.active_events.values()
        ]
        
        game_state = {
            "player": {
                "id": player.id,
                "username": player.username,
                "level": player.level,
                "credits": player.credits,
                "reputation": player.reputation,
                "current_location": {
                    "id": player.current_location.id,
                    "name": player.current_location.name
                } if player.current_location else None
            },
            "vehicles": [
                {
                    "id": vehicle.id,
                    "name": vehicle.name,
                    "type": vehicle.vehicle_type.value,
                    "location_id": vehicle.current_location_id,
                    "is_traveling": vehicle.is_traveling,
                    "fuel": vehicle.current_fuel,
                    "durability": vehicle.durability
                }
                for vehicle in player.vehicles
            ],
            "active_events": active_events,
            "server_time": datetime.utcnow().isoformat()
        }
        
        await self.websocket_manager.send_game_state_update(player_id, game_state)
