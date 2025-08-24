"""Player-related Celery tasks."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc

from ..celery_app import celery_app
from ..database import AsyncSessionLocal
from ..models import Player, Mission, CombatLog, Vehicle, MissionStatus
from ..aws_services import aws_services

logger = logging.getLogger(__name__)


@celery_app.task
def process_player_action(player_id: int, action_type: str, action_data: Dict[str, Any]):
    """Process a player action asynchronously."""
    try:
        import asyncio
        return asyncio.run(_process_player_action_async(player_id, action_type, action_data))
    except Exception as e:
        logger.error(f"Failed to process player action: {e}")
        return {"error": str(e)}


async def _process_player_action_async(player_id: int, action_type: str, action_data: Dict[str, Any]):
    """Async player action processing."""
    async with AsyncSessionLocal() as db:
        # Get player
        result = await db.execute(
            select(Player)
            .options(
                selectinload(Player.vehicles),
                selectinload(Player.missions)
            )
            .where(Player.id == player_id)
        )
        player = result.scalar_one_or_none()
        
        if not player:
            return {"error": "Player not found"}
        
        # Process different action types
        if action_type == "level_up_check":
            return await _check_level_up(player, db)
        elif action_type == "daily_bonus":
            return await _process_daily_bonus(player, db)
        elif action_type == "achievement_check":
            return await _check_achievements(player, db)
        elif action_type == "reputation_update":
            return await _update_reputation(player, action_data, db)
        else:
            return {"error": f"Unknown action type: {action_type}"}


async def _check_level_up(player: Player, db):
    """Check if player should level up."""
    experience_for_next_level = player.level * 1000
    levels_gained = 0
    
    while player.experience >= experience_for_next_level:
        player.level += 1
        player.experience -= experience_for_next_level
        levels_gained += 1
        
        # Award level up bonus
        level_bonus = player.level * 100
        player.credits += level_bonus
        
        # Recalculate experience needed for next level
        experience_for_next_level = player.level * 1000
    
    if levels_gained > 0:
        await db.commit()
        
        # Log level up event
        await aws_services.s3.upload_game_log({
            "player_id": player.id,
            "event_type": "level_up",
            "new_level": player.level,
            "levels_gained": levels_gained,
            "bonus_credits": levels_gained * player.level * 100,
            "timestamp": datetime.utcnow().isoformat()
        }, "player_progression")
        
        return {
            "leveled_up": True,
            "new_level": player.level,
            "levels_gained": levels_gained,
            "bonus_credits": levels_gained * player.level * 100
        }
    
    return {"leveled_up": False}


async def _process_daily_bonus(player: Player, db):
    """Process daily login bonus."""
    # Check if player already received bonus today
    today = datetime.utcnow().date()
    last_bonus_date = getattr(player, 'last_daily_bonus', None)
    
    if last_bonus_date and last_bonus_date == today:
        return {"bonus_received": False, "reason": "Already received today"}
    
    # Calculate bonus based on consecutive days
    consecutive_days = getattr(player, 'consecutive_login_days', 0) + 1
    base_bonus = 100
    bonus_credits = base_bonus * min(consecutive_days, 7)  # Max 7x multiplier
    
    # Award bonus
    player.credits += bonus_credits
    player.last_daily_bonus = today
    player.consecutive_login_days = consecutive_days
    
    await db.commit()
    
    # Log daily bonus
    await aws_services.s3.upload_game_log({
        "player_id": player.id,
        "event_type": "daily_bonus",
        "bonus_credits": bonus_credits,
        "consecutive_days": consecutive_days,
        "timestamp": datetime.utcnow().isoformat()
    }, "player_bonuses")
    
    return {
        "bonus_received": True,
        "bonus_credits": bonus_credits,
        "consecutive_days": consecutive_days,
        "new_credits": player.credits
    }


async def _check_achievements(player: Player, db):
    """Check and award achievements."""
    achievements_earned = []
    
    # Mission-based achievements
    completed_missions = len([m for m in player.missions if m.status == MissionStatus.COMPLETED])
    
    mission_achievements = [
        (10, "First Steps", "Complete 10 missions"),
        (50, "Experienced Trader", "Complete 50 missions"),
        (100, "Master Transporter", "Complete 100 missions"),
        (500, "Legendary Hauler", "Complete 500 missions")
    ]
    
    for threshold, title, description in mission_achievements:
        if completed_missions >= threshold:
            # Check if already earned
            if not hasattr(player, 'achievements') or title not in (player.achievements or {}):
                if not player.achievements:
                    player.achievements = {}
                
                player.achievements[title] = {
                    "description": description,
                    "earned_at": datetime.utcnow().isoformat(),
                    "reward_credits": threshold * 10
                }
                
                player.credits += threshold * 10
                achievements_earned.append({
                    "title": title,
                    "description": description,
                    "reward_credits": threshold * 10
                })
    
    # Combat achievements
    combat_wins = len([c for c in player.combat_logs if c.winner_id == player.id])
    
    combat_achievements = [
        (5, "First Blood", "Win 5 combat encounters"),
        (25, "Warrior", "Win 25 combat encounters"),
        (100, "Combat Veteran", "Win 100 combat encounters")
    ]
    
    for threshold, title, description in combat_achievements:
        if combat_wins >= threshold:
            if not hasattr(player, 'achievements') or title not in (player.achievements or {}):
                if not player.achievements:
                    player.achievements = {}
                
                player.achievements[title] = {
                    "description": description,
                    "earned_at": datetime.utcnow().isoformat(),
                    "reward_credits": threshold * 20
                }
                
                player.credits += threshold * 20
                achievements_earned.append({
                    "title": title,
                    "description": description,
                    "reward_credits": threshold * 20
                })
    
    # Wealth achievements
    wealth_achievements = [
        (10000, "Entrepreneur", "Accumulate 10,000 credits"),
        (100000, "Tycoon", "Accumulate 100,000 credits"),
        (1000000, "Magnate", "Accumulate 1,000,000 credits")
    ]
    
    for threshold, title, description in wealth_achievements:
        if player.credits >= threshold:
            if not hasattr(player, 'achievements') or title not in (player.achievements or {}):
                if not player.achievements:
                    player.achievements = {}
                
                player.achievements[title] = {
                    "description": description,
                    "earned_at": datetime.utcnow().isoformat(),
                    "reward_reputation": threshold // 1000
                }
                
                player.reputation += threshold // 1000
                achievements_earned.append({
                    "title": title,
                    "description": description,
                    "reward_reputation": threshold // 1000
                })
    
    if achievements_earned:
        await db.commit()
        
        # Log achievements
        await aws_services.s3.upload_game_log({
            "player_id": player.id,
            "event_type": "achievements_earned",
            "achievements": achievements_earned,
            "timestamp": datetime.utcnow().isoformat()
        }, "player_achievements")
    
    return {
        "achievements_earned": len(achievements_earned),
        "new_achievements": achievements_earned
    }


async def _update_reputation(player: Player, action_data: Dict[str, Any], db):
    """Update player reputation based on actions."""
    reputation_change = action_data.get("reputation_change", 0)
    reason = action_data.get("reason", "Unknown")
    
    old_reputation = player.reputation
    player.reputation = max(0, player.reputation + reputation_change)
    
    await db.commit()
    
    # Log reputation change
    await aws_services.s3.upload_game_log({
        "player_id": player.id,
        "event_type": "reputation_change",
        "old_reputation": old_reputation,
        "new_reputation": player.reputation,
        "change": reputation_change,
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat()
    }, "player_reputation")
    
    return {
        "reputation_updated": True,
        "old_reputation": old_reputation,
        "new_reputation": player.reputation,
        "change": reputation_change
    }


@celery_app.task
def update_player_rankings():
    """Update global player rankings."""
    try:
        import asyncio
        return asyncio.run(_update_player_rankings_async())
    except Exception as e:
        logger.error(f"Failed to update player rankings: {e}")
        return {"error": str(e)}


async def _update_player_rankings_async():
    """Async player ranking updates."""
    async with AsyncSessionLocal() as db:
        # Get top players by different metrics
        rankings = {}
        
        # Credits ranking
        result = await db.execute(
            select(Player)
            .order_by(desc(Player.credits))
            .limit(100)
        )
        top_credits = result.scalars().all()
        
        rankings["credits"] = [
            {
                "rank": idx + 1,
                "player_id": player.id,
                "username": player.username,
                "value": player.credits
            }
            for idx, player in enumerate(top_credits)
        ]
        
        # Reputation ranking
        result = await db.execute(
            select(Player)
            .order_by(desc(Player.reputation))
            .limit(100)
        )
        top_reputation = result.scalars().all()
        
        rankings["reputation"] = [
            {
                "rank": idx + 1,
                "player_id": player.id,
                "username": player.username,
                "value": player.reputation
            }
            for idx, player in enumerate(top_reputation)
        ]
        
        # Level ranking
        result = await db.execute(
            select(Player)
            .order_by(desc(Player.level), desc(Player.experience))
            .limit(100)
        )
        top_level = result.scalars().all()
        
        rankings["level"] = [
            {
                "rank": idx + 1,
                "player_id": player.id,
                "username": player.username,
                "value": player.level
            }
            for idx, player in enumerate(top_level)
        ]
        
        # Store rankings in S3
        rankings_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "rankings": rankings,
            "total_players": len(set(
                [p["player_id"] for ranking in rankings.values() for p in ranking]
            ))
        }
        
        await aws_services.s3.upload_game_log(rankings_data, "player_rankings")
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("PlayerRankingsUpdated", 1)
        
        return {
            "rankings_updated": True,
            "categories": list(rankings.keys()),
            "total_ranked_players": rankings_data["total_players"]
        }


@celery_app.task
def process_inactive_players():
    """Process inactive players and apply penalties."""
    try:
        import asyncio
        return asyncio.run(_process_inactive_players_async())
    except Exception as e:
        logger.error(f"Failed to process inactive players: {e}")
        return {"error": str(e)}


async def _process_inactive_players_async():
    """Async inactive player processing."""
    async with AsyncSessionLocal() as db:
        # Find players inactive for more than 7 days
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        result = await db.execute(
            select(Player).where(
                Player.last_active < cutoff_date,
                Player.is_online == False
            )
        )
        inactive_players = result.scalars().all()
        
        processed_count = 0
        
        for player in inactive_players:
            # Apply inactivity penalties
            days_inactive = (datetime.utcnow() - player.last_active).days
            
            if days_inactive >= 30:
                # Severe penalty for 30+ days
                reputation_penalty = min(player.reputation // 4, 50)
                player.reputation = max(0, player.reputation - reputation_penalty)
                processed_count += 1
            elif days_inactive >= 14:
                # Moderate penalty for 14+ days
                reputation_penalty = min(player.reputation // 8, 25)
                player.reputation = max(0, player.reputation - reputation_penalty)
                processed_count += 1
            elif days_inactive >= 7:
                # Light penalty for 7+ days
                reputation_penalty = min(player.reputation // 16, 10)
                player.reputation = max(0, player.reputation - reputation_penalty)
                processed_count += 1
        
        await db.commit()
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("InactivePlayersProcessed", processed_count)
        
        return {
            "inactive_players_found": len(inactive_players),
            "players_penalized": processed_count
        }


@celery_app.task
def calculate_player_statistics():
    """Calculate comprehensive player statistics."""
    try:
        import asyncio
        return asyncio.run(_calculate_player_statistics_async())
    except Exception as e:
        logger.error(f"Failed to calculate player statistics: {e}")
        return {"error": str(e)}


async def _calculate_player_statistics_async():
    """Async player statistics calculation."""
    async with AsyncSessionLocal() as db:
        # Get overall game statistics
        total_players_result = await db.execute(select(func.count(Player.id)))
        total_players = total_players_result.scalar()
        
        active_players_result = await db.execute(
            select(func.count(Player.id)).where(
                Player.last_active >= datetime.utcnow() - timedelta(days=7)
            )
        )
        active_players = active_players_result.scalar()
        
        online_players_result = await db.execute(
            select(func.count(Player.id)).where(Player.is_online == True)
        )
        online_players = online_players_result.scalar()
        
        # Calculate average stats
        avg_level_result = await db.execute(select(func.avg(Player.level)))
        avg_level = avg_level_result.scalar() or 0
        
        avg_credits_result = await db.execute(select(func.avg(Player.credits)))
        avg_credits = avg_credits_result.scalar() or 0
        
        avg_reputation_result = await db.execute(select(func.avg(Player.reputation)))
        avg_reputation = avg_reputation_result.scalar() or 0
        
        # Mission statistics
        total_missions_result = await db.execute(select(func.count(Mission.id)))
        total_missions = total_missions_result.scalar()
        
        completed_missions_result = await db.execute(
            select(func.count(Mission.id)).where(Mission.status == MissionStatus.COMPLETED)
        )
        completed_missions = completed_missions_result.scalar()
        
        # Combat statistics
        total_combats_result = await db.execute(select(func.count(CombatLog.id)))
        total_combats = total_combats_result.scalar()
        
        # Vehicle statistics
        total_vehicles_result = await db.execute(select(func.count(Vehicle.id)))
        total_vehicles = total_vehicles_result.scalar()
        
        statistics = {
            "timestamp": datetime.utcnow().isoformat(),
            "player_stats": {
                "total_players": total_players,
                "active_players_7d": active_players,
                "online_players": online_players,
                "avg_level": round(float(avg_level), 2),
                "avg_credits": round(float(avg_credits), 2),
                "avg_reputation": round(float(avg_reputation), 2)
            },
            "game_stats": {
                "total_missions": total_missions,
                "completed_missions": completed_missions,
                "mission_completion_rate": round(completed_missions / max(total_missions, 1) * 100, 2),
                "total_combats": total_combats,
                "total_vehicles": total_vehicles,
                "avg_vehicles_per_player": round(total_vehicles / max(total_players, 1), 2)
            }
        }
        
        # Store statistics
        await aws_services.s3.upload_game_log(statistics, "game_statistics")
        
        # Send metrics to CloudWatch
        metrics = {
            "TotalPlayers": total_players,
            "ActivePlayers": active_players,
            "OnlinePlayers": online_players,
            "AverageLevel": avg_level,
            "TotalMissions": total_missions,
            "CompletedMissions": completed_missions,
            "TotalCombats": total_combats,
            "TotalVehicles": total_vehicles
        }
        
        await aws_services.cloudwatch.put_game_metrics(metrics)
        
        return statistics
