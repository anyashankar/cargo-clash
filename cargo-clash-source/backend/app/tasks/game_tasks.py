"""Game-related Celery tasks."""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..celery_app import celery_app
from ..database import AsyncSessionLocal
from ..models import (
    Player, Vehicle, Mission, Location, GameEvent, CombatLog,
    MissionStatus, GameEventType, CargoType
)
from ..aws_services import aws_services

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def process_combat(self, attacker_id: int, target_id: int, combat_data: Dict[str, Any]):
    """Process combat between players asynchronously."""
    try:
        import asyncio
        return asyncio.run(_process_combat_async(attacker_id, target_id, combat_data))
    except Exception as e:
        logger.error(f"Combat processing failed: {e}")
        self.retry(countdown=60, max_retries=3)


async def _process_combat_async(attacker_id: int, target_id: int, combat_data: Dict[str, Any]):
    """Async combat processing logic."""
    async with AsyncSessionLocal() as db:
        # Get players and their vehicles
        attacker_result = await db.execute(
            select(Player)
            .options(selectinload(Player.vehicles))
            .where(Player.id == attacker_id)
        )
        attacker = attacker_result.scalar_one_or_none()
        
        target_result = await db.execute(
            select(Player)
            .options(selectinload(Player.vehicles))
            .where(Player.id == target_id)
        )
        target = target_result.scalar_one_or_none()
        
        if not attacker or not target:
            return {"error": "Player not found"}
        
        # Execute combat logic
        combat_result = await _execute_combat_logic(attacker, target, combat_data, db)
        
        # Log combat event
        await aws_services.log_combat_event({
            "attacker_id": attacker_id,
            "target_id": target_id,
            "result": combat_result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        await db.commit()
        return combat_result


async def _execute_combat_logic(attacker: Player, target: Player, combat_data: Dict[str, Any], db: AsyncSession):
    """Execute the actual combat logic."""
    # Simplified combat logic - expand as needed
    attacker_power = sum(v.attack_power for v in attacker.vehicles)
    target_power = sum(v.attack_power for v in target.vehicles)
    
    # Add randomness
    attacker_roll = attacker_power * random.uniform(0.8, 1.2)
    target_roll = target_power * random.uniform(0.8, 1.2)
    
    winner_id = attacker.id if attacker_roll > target_roll else target.id
    
    # Apply damage and rewards
    if winner_id == attacker.id:
        # Attacker wins
        credits_gained = min(target.credits // 10, 1000)  # Max 10% or 1000 credits
        attacker.credits += credits_gained
        target.credits = max(0, target.credits - credits_gained)
        attacker.experience += 100
        attacker.reputation += 2
        target.reputation = max(0, target.reputation - 1)
    else:
        # Target wins (defender bonus)
        credits_gained = min(attacker.credits // 20, 500)  # Smaller penalty for attacker
        target.credits += credits_gained
        attacker.credits = max(0, attacker.credits - credits_gained)
        target.experience += 75
        target.reputation += 1
    
    return {
        "winner_id": winner_id,
        "attacker_id": attacker.id,
        "target_id": target.id,
        "credits_transferred": credits_gained,
        "timestamp": datetime.utcnow().isoformat()
    }


@celery_app.task
def process_expired_missions():
    """Process missions that have expired."""
    try:
        import asyncio
        return asyncio.run(_process_expired_missions_async())
    except Exception as e:
        logger.error(f"Failed to process expired missions: {e}")
        return {"error": str(e)}


async def _process_expired_missions_async():
    """Async expired missions processing."""
    async with AsyncSessionLocal() as db:
        current_time = datetime.utcnow()
        
        # Get expired missions
        result = await db.execute(
            select(Mission)
            .options(selectinload(Mission.player))
            .where(
                Mission.status.in_([MissionStatus.ACCEPTED, MissionStatus.IN_PROGRESS]),
                Mission.deadline <= current_time
            )
        )
        expired_missions = result.scalars().all()
        
        processed_count = 0
        for mission in expired_missions:
            mission.status = MissionStatus.FAILED
            
            if mission.player:
                # Apply penalty
                penalty = mission.penalty_credits or (mission.reward_credits // 4)
                mission.player.credits = max(0, mission.player.credits - penalty)
                mission.player.reputation = max(0, mission.player.reputation - 2)
                
                # Log mission failure
                await aws_services.s3.upload_game_log({
                    "mission_id": mission.id,
                    "player_id": mission.player.id,
                    "status": "expired",
                    "penalty": penalty,
                    "timestamp": current_time.isoformat()
                }, "mission_failures")
                
                processed_count += 1
        
        await db.commit()
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("ExpiredMissions", processed_count)
        
        return {"processed_missions": processed_count}


@celery_app.task
def generate_random_events():
    """Generate random world events."""
    try:
        import asyncio
        return asyncio.run(_generate_random_events_async())
    except Exception as e:
        logger.error(f"Failed to generate random events: {e}")
        return {"error": str(e)}


async def _generate_random_events_async():
    """Async random event generation."""
    async with AsyncSessionLocal() as db:
        # 20% chance of generating an event
        if random.random() > 0.2:
            return {"event_generated": False}
        
        # Get random locations
        result = await db.execute(
            select(Location).where(Location.is_active == True).limit(20)
        )
        locations = result.scalars().all()
        
        if not locations:
            return {"error": "No active locations found"}
        
        # Select event type
        event_types = [
            GameEventType.MARKET_SHIFT,
            GameEventType.WEATHER_CHANGE,
            GameEventType.PIRATE_ATTACK,
            GameEventType.TRADE_ROUTE_BLOCKED
        ]
        
        event_type = random.choice(event_types)
        affected_locations = random.sample(locations, min(3, len(locations)))
        affected_location_ids = [loc.id for loc in affected_locations]
        
        # Create event
        event = await _create_game_event(event_type, affected_location_ids, db)
        
        if event:
            await db.commit()
            
            # Send event to SQS for real-time processing
            await aws_services.sqs.send_game_event("world_event", {
                "event_id": event.id,
                "event_type": event.event_type.value,
                "title": event.title,
                "description": event.description,
                "affected_locations": affected_location_ids,
                "severity": event.severity
            })
            
            return {
                "event_generated": True,
                "event_id": event.id,
                "event_type": event.event_type.value,
                "affected_locations": len(affected_location_ids)
            }
        
        return {"event_generated": False}


async def _create_game_event(event_type: GameEventType, location_ids: List[int], db: AsyncSession) -> GameEvent:
    """Create a specific type of game event."""
    if event_type == GameEventType.MARKET_SHIFT:
        cargo_type = random.choice(list(CargoType))
        shift_direction = random.choice(["surge", "crash"])
        
        event = GameEvent(
            event_type=event_type,
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
        
    elif event_type == GameEventType.WEATHER_CHANGE:
        weather_types = ["storm", "fog", "hurricane", "blizzard"]
        weather_type = random.choice(weather_types)
        
        event = GameEvent(
            event_type=event_type,
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
        
    elif event_type == GameEventType.PIRATE_ATTACK:
        event = GameEvent(
            event_type=event_type,
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
        
    elif event_type == GameEventType.TRADE_ROUTE_BLOCKED:
        event = GameEvent(
            event_type=event_type,
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
    await db.flush()
    return event


@celery_app.task
def process_vehicle_travel(vehicle_id: int):
    """Process vehicle travel completion."""
    try:
        import asyncio
        return asyncio.run(_process_vehicle_travel_async(vehicle_id))
    except Exception as e:
        logger.error(f"Failed to process vehicle travel: {e}")
        return {"error": str(e)}


async def _process_vehicle_travel_async(vehicle_id: int):
    """Async vehicle travel processing."""
    async with AsyncSessionLocal() as db:
        # Get vehicle
        result = await db.execute(
            select(Vehicle)
            .options(
                selectinload(Vehicle.owner),
                selectinload(Vehicle.current_location),
                selectinload(Vehicle.destination)
            )
            .where(Vehicle.id == vehicle_id)
        )
        vehicle = result.scalar_one_or_none()
        
        if not vehicle or not vehicle.is_traveling:
            return {"error": "Vehicle not found or not traveling"}
        
        # Check if arrival time has passed
        if vehicle.estimated_arrival and datetime.utcnow() >= vehicle.estimated_arrival:
            # Complete travel
            vehicle.is_traveling = False
            vehicle.current_location_id = vehicle.destination_id
            vehicle.destination_id = None
            vehicle.travel_start_time = None
            vehicle.estimated_arrival = None
            
            # Update player location
            if vehicle.owner:
                vehicle.owner.current_location_id = vehicle.current_location_id
            
            await db.commit()
            
            # Send completion event
            await aws_services.sqs.send_game_event("travel_complete", {
                "vehicle_id": vehicle_id,
                "player_id": vehicle.owner.id if vehicle.owner else None,
                "location_id": vehicle.current_location_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return {
                "travel_completed": True,
                "vehicle_id": vehicle_id,
                "new_location_id": vehicle.current_location_id
            }
        
        return {"travel_completed": False, "vehicle_id": vehicle_id}


@celery_app.task
def process_mission_generation():
    """Generate new missions for players."""
    try:
        import asyncio
        return asyncio.run(_process_mission_generation_async())
    except Exception as e:
        logger.error(f"Failed to generate missions: {e}")
        return {"error": str(e)}


async def _process_mission_generation_async():
    """Async mission generation."""
    async with AsyncSessionLocal() as db:
        # Get active locations
        result = await db.execute(
            select(Location).where(Location.is_active == True)
        )
        locations = result.scalars().all()
        
        if len(locations) < 2:
            return {"error": "Need at least 2 locations for missions"}
        
        # Count current available missions
        result = await db.execute(
            select(Mission).where(Mission.status == MissionStatus.AVAILABLE)
        )
        available_missions = len(result.scalars().all())
        
        # Generate missions if we have fewer than 50 available
        missions_to_generate = max(0, 50 - available_missions)
        generated_count = 0
        
        for _ in range(missions_to_generate):
            origin = random.choice(locations)
            destination = random.choice([loc for loc in locations if loc.id != origin.id])
            
            # Generate mission parameters
            cargo_type = random.choice(list(CargoType))
            quantity = random.randint(10, 100)
            difficulty = random.randint(1, 10)
            
            # Calculate rewards based on distance and difficulty
            distance = ((destination.x_coordinate - origin.x_coordinate) ** 2 + 
                       (destination.y_coordinate - origin.y_coordinate) ** 2) ** 0.5
            
            base_reward = int(distance * 10 + difficulty * 50)
            reward_credits = random.randint(base_reward, base_reward * 2)
            reward_experience = reward_credits // 10
            
            mission = Mission(
                title=f"Transport {cargo_type.value.title()} to {destination.name}",
                description=f"Deliver {quantity} units of {cargo_type.value} from {origin.name} to {destination.name}",
                mission_type="transport",
                origin_id=origin.id,
                destination_id=destination.id,
                required_cargo={cargo_type.value: quantity},
                cargo_value=quantity * 50,
                difficulty=difficulty,
                reward_credits=reward_credits,
                reward_experience=reward_experience,
                min_level=max(1, difficulty - 2),
                time_limit=int(distance * 2 + 60)  # Time limit based on distance
            )
            
            # Set deadline
            mission.deadline = datetime.utcnow() + timedelta(minutes=mission.time_limit)
            
            db.add(mission)
            generated_count += 1
        
        await db.commit()
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("MissionsGenerated", generated_count)
        
        return {
            "missions_generated": generated_count,
            "total_available": available_missions + generated_count
        }
