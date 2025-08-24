"""Combat system routes."""

import random
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..auth import get_current_user, permission_checker
from ..database import get_async_db
from ..models import Player, Vehicle, CombatLog, Location
from ..schemas import CombatAction, CombatResult

router = APIRouter()


@router.post("/attack/{target_player_id}", response_model=CombatResult)
async def attack_player(
    target_player_id: int,
    attacker_vehicle_id: int,
    combat_action: CombatAction,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Attack another player."""
    # Get target player
    result = await db.execute(
        select(Player)
        .options(selectinload(Player.vehicles))
        .where(Player.id == target_player_id)
    )
    target_player = result.scalar_one_or_none()
    
    if not target_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target player not found"
        )
    
    # Check if attack is allowed
    if not permission_checker.can_attack_player(current_user, target_player):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot attack this player"
        )
    
    # Get attacker vehicle
    result = await db.execute(
        select(Vehicle)
        .options(selectinload(Vehicle.current_location))
        .where(
            Vehicle.id == attacker_vehicle_id,
            Vehicle.owner_id == current_user.id
        )
    )
    attacker_vehicle = result.scalar_one_or_none()
    
    if not attacker_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attacker vehicle not found or not owned by you"
        )
    
    # Get target vehicle (assume first available vehicle)
    target_vehicle = None
    for vehicle in target_player.vehicles:
        if vehicle.current_location_id == attacker_vehicle.current_location_id:
            target_vehicle = vehicle
            break
    
    if not target_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No target vehicle at the same location"
        )
    
    # Check if both vehicles are at the same location
    if attacker_vehicle.current_location_id != target_vehicle.current_location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicles must be at the same location for combat"
        )
    
    # Execute combat
    combat_result = await _execute_combat(
        attacker_vehicle, target_vehicle, combat_action, db
    )
    
    # Create combat log
    combat_log = CombatLog(
        player_id=current_user.id,
        opponent_type="player",
        opponent_id=target_player.id,
        location_id=attacker_vehicle.current_location_id,
        combat_type="attack",
        winner_id=combat_result.winner_id,
        damage_dealt=combat_result.damage_dealt,
        damage_received=combat_result.damage_received,
        cargo_lost=combat_result.cargo_lost,
        cargo_gained=combat_result.cargo_gained,
        credits_lost=combat_result.credits_lost,
        credits_gained=combat_result.credits_gained,
        combat_data={
            "action": combat_action.dict(),
            "attacker_vehicle_id": attacker_vehicle.id,
            "target_vehicle_id": target_vehicle.id
        }
    )
    
    db.add(combat_log)
    await db.commit()
    
    return combat_result


@router.post("/defend", response_model=CombatResult)
async def defend_against_attack(
    attacker_player_id: int,
    defender_vehicle_id: int,
    combat_action: CombatAction,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Defend against an attack (reactive combat)."""
    # This would be called in response to an attack
    # Implementation would be similar to attack but with defensive bonuses
    
    # Get attacker player
    result = await db.execute(
        select(Player).where(Player.id == attacker_player_id)
    )
    attacker_player = result.scalar_one_or_none()
    
    if not attacker_player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attacker player not found"
        )
    
    # Get defender vehicle
    result = await db.execute(
        select(Vehicle).where(
            Vehicle.id == defender_vehicle_id,
            Vehicle.owner_id == current_user.id
        )
    )
    defender_vehicle = result.scalar_one_or_none()
    
    if not defender_vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Defender vehicle not found or not owned by you"
        )
    
    # Defensive combat logic would go here
    # For now, return a basic result
    return CombatResult(
        winner_id=current_user.id,
        damage_dealt=0,
        damage_received=10,
        experience_gained=50
    )


@router.post("/pirate-encounter/{vehicle_id}", response_model=CombatResult)
async def handle_pirate_encounter(
    vehicle_id: int,
    combat_action: CombatAction,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Handle encounter with NPC pirates."""
    # Get vehicle
    result = await db.execute(
        select(Vehicle)
        .options(selectinload(Vehicle.current_location))
        .where(
            Vehicle.id == vehicle_id,
            Vehicle.owner_id == current_user.id
        )
    )
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found or not owned by you"
        )
    
    # Generate pirate stats based on location danger level
    location = vehicle.current_location
    danger_level = location.danger_level if location else 1
    
    pirate_stats = {
        "attack_power": 10 + (danger_level * 5),
        "defense": 5 + (danger_level * 3),
        "durability": 50 + (danger_level * 10)
    }
    
    # Execute combat against pirates
    combat_result = await _execute_pirate_combat(
        vehicle, pirate_stats, combat_action, db
    )
    
    # Create combat log
    combat_log = CombatLog(
        player_id=current_user.id,
        opponent_type="pirate",
        location_id=vehicle.current_location_id,
        combat_type="defense",
        winner_id=combat_result.winner_id,
        damage_dealt=combat_result.damage_dealt,
        damage_received=combat_result.damage_received,
        cargo_lost=combat_result.cargo_lost,
        cargo_gained=combat_result.cargo_gained,
        credits_lost=combat_result.credits_lost,
        credits_gained=combat_result.credits_gained,
        combat_data={
            "action": combat_action.dict(),
            "pirate_stats": pirate_stats,
            "danger_level": danger_level
        }
    )
    
    db.add(combat_log)
    await db.commit()
    
    return combat_result


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_combat_history(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Get player's combat history."""
    result = await db.execute(
        select(CombatLog)
        .options(selectinload(CombatLog.location))
        .where(CombatLog.player_id == current_user.id)
        .order_by(CombatLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    combat_logs = result.scalars().all()
    
    history = []
    for log in combat_logs:
        history.append({
            "id": log.id,
            "opponent_type": log.opponent_type,
            "opponent_id": log.opponent_id,
            "location": log.location.name if log.location else "Unknown",
            "combat_type": log.combat_type,
            "winner_id": log.winner_id,
            "was_winner": log.winner_id == current_user.id,
            "damage_dealt": log.damage_dealt,
            "damage_received": log.damage_received,
            "cargo_lost": log.cargo_lost,
            "cargo_gained": log.cargo_gained,
            "credits_lost": log.credits_lost,
            "credits_gained": log.credits_gained,
            "created_at": log.created_at
        })
    
    return history


@router.get("/stats")
async def get_combat_stats(
    current_user: Player = Depends(get_current_user)
):
    """Get player's combat statistics."""
    combat_logs = current_user.combat_logs
    
    total_combats = len(combat_logs)
    wins = len([log for log in combat_logs if log.winner_id == current_user.id])
    losses = total_combats - wins
    
    total_damage_dealt = sum(log.damage_dealt for log in combat_logs)
    total_damage_received = sum(log.damage_received for log in combat_logs)
    total_credits_gained = sum(log.credits_gained for log in combat_logs)
    total_credits_lost = sum(log.credits_lost for log in combat_logs)
    
    return {
        "total_combats": total_combats,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / max(total_combats, 1) * 100, 2),
        "total_damage_dealt": total_damage_dealt,
        "total_damage_received": total_damage_received,
        "average_damage_per_combat": round(total_damage_dealt / max(total_combats, 1), 2),
        "total_credits_gained": total_credits_gained,
        "total_credits_lost": total_credits_lost,
        "net_credits": total_credits_gained - total_credits_lost
    }


async def _execute_combat(
    attacker_vehicle: Vehicle,
    target_vehicle: Vehicle,
    combat_action: CombatAction,
    db: AsyncSession
) -> CombatResult:
    """Execute combat between two vehicles."""
    # Calculate base damage
    base_damage = attacker_vehicle.attack_power
    
    # Apply action modifiers
    if combat_action.action_type == "attack":
        damage_multiplier = 1.0
    elif combat_action.action_type == "special_ability":
        damage_multiplier = 1.5  # Special abilities do more damage
    else:
        damage_multiplier = 0.8  # Defensive actions do less damage
    
    # Add randomness
    damage_variance = random.uniform(0.8, 1.2)
    final_damage = int(base_damage * damage_multiplier * damage_variance)
    
    # Apply target defense
    damage_after_defense = max(1, final_damage - target_vehicle.defense)
    
    # Apply damage to target
    target_vehicle.durability = max(0, target_vehicle.durability - damage_after_defense)
    
    # Calculate counter-attack damage
    counter_damage = max(1, target_vehicle.attack_power - attacker_vehicle.defense)
    counter_damage = int(counter_damage * random.uniform(0.5, 0.8))  # Counter-attacks are weaker
    
    attacker_vehicle.durability = max(0, attacker_vehicle.durability - counter_damage)
    
    # Determine winner
    winner_id = None
    if target_vehicle.durability == 0:
        winner_id = attacker_vehicle.owner_id
    elif attacker_vehicle.durability == 0:
        winner_id = target_vehicle.owner_id
    
    # Calculate loot if there's a winner
    cargo_lost = {}
    cargo_gained = {}
    credits_lost = 0
    credits_gained = 0
    
    if winner_id == attacker_vehicle.owner_id:
        # Attacker wins - gets some of target's cargo
        target_cargo = target_vehicle.current_cargo or {}
        for cargo_type, quantity in target_cargo.items():
            stolen_amount = min(quantity, quantity // 4)  # Steal up to 25%
            if stolen_amount > 0:
                cargo_gained[cargo_type] = stolen_amount
                cargo_lost[cargo_type] = stolen_amount
                target_cargo[cargo_type] -= stolen_amount
        
        target_vehicle.current_cargo = target_cargo
        
        # Add stolen cargo to attacker
        attacker_cargo = attacker_vehicle.current_cargo or {}
        for cargo_type, quantity in cargo_gained.items():
            attacker_cargo[cargo_type] = attacker_cargo.get(cargo_type, 0) + quantity
        attacker_vehicle.current_cargo = attacker_cargo
        
        credits_gained = 100  # Base reward for winning
    
    await db.commit()
    
    return CombatResult(
        winner_id=winner_id,
        damage_dealt=damage_after_defense,
        damage_received=counter_damage,
        cargo_lost=cargo_lost,
        cargo_gained=cargo_gained,
        credits_lost=credits_lost,
        credits_gained=credits_gained,
        experience_gained=50 if winner_id == attacker_vehicle.owner_id else 25
    )


async def _execute_pirate_combat(
    vehicle: Vehicle,
    pirate_stats: Dict[str, int],
    combat_action: CombatAction,
    db: AsyncSession
) -> CombatResult:
    """Execute combat against NPC pirates."""
    # Player damage to pirates
    base_damage = vehicle.attack_power
    
    if combat_action.action_type == "attack":
        damage_multiplier = 1.0
    elif combat_action.action_type == "special_ability":
        damage_multiplier = 1.5
    else:
        damage_multiplier = 0.8
    
    damage_variance = random.uniform(0.8, 1.2)
    player_damage = int(base_damage * damage_multiplier * damage_variance)
    player_damage = max(1, player_damage - pirate_stats["defense"])
    
    # Pirate damage to player
    pirate_damage = max(1, pirate_stats["attack_power"] - vehicle.defense)
    pirate_damage = int(pirate_damage * random.uniform(0.7, 1.0))
    
    # Apply damage
    pirate_stats["durability"] -= player_damage
    vehicle.durability = max(0, vehicle.durability - pirate_damage)
    
    # Determine winner
    winner_id = None
    if pirate_stats["durability"] <= 0:
        winner_id = vehicle.owner_id
    elif vehicle.durability == 0:
        winner_id = None  # Pirates win
    
    # Calculate rewards/losses
    cargo_lost = {}
    cargo_gained = {}
    credits_lost = 0
    credits_gained = 0
    
    if winner_id == vehicle.owner_id:
        # Player wins
        credits_gained = random.randint(50, 200)
        # Chance to find rare cargo
        if random.random() < 0.3:
            cargo_gained["artifacts"] = 1
    else:
        # Pirates win - player loses some cargo
        current_cargo = vehicle.current_cargo or {}
        for cargo_type, quantity in current_cargo.items():
            lost_amount = min(quantity, quantity // 3)  # Lose up to 33%
            if lost_amount > 0:
                cargo_lost[cargo_type] = lost_amount
                current_cargo[cargo_type] -= lost_amount
        
        vehicle.current_cargo = current_cargo
        credits_lost = random.randint(100, 500)
    
    await db.commit()
    
    return CombatResult(
        winner_id=winner_id,
        damage_dealt=player_damage,
        damage_received=pirate_damage,
        cargo_lost=cargo_lost,
        cargo_gained=cargo_gained,
        credits_lost=credits_lost,
        credits_gained=credits_gained,
        experience_gained=75 if winner_id == vehicle.owner_id else 25
    )
