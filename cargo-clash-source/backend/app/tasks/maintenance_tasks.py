"""Maintenance and cleanup Celery tasks."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, delete

from ..celery_app import celery_app
from ..database import AsyncSessionLocal
from ..models import (
    Player, Mission, GameEvent, CombatLog, MarketPrice,
    MissionStatus, Vehicle
)
from ..aws_services import aws_services

logger = logging.getLogger(__name__)


@celery_app.task
def cleanup_old_data():
    """Clean up old data to maintain database performance."""
    try:
        import asyncio
        return asyncio.run(_cleanup_old_data_async())
    except Exception as e:
        logger.error(f"Failed to cleanup old data: {e}")
        return {"error": str(e)}


async def _cleanup_old_data_async():
    """Async old data cleanup."""
    async with AsyncSessionLocal() as db:
        cleanup_stats = {
            "old_missions": 0,
            "old_events": 0,
            "old_combat_logs": 0,
            "old_price_history": 0
        }
        
        # Clean up old completed/failed missions (older than 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        old_missions_result = await db.execute(
            delete(Mission).where(
                Mission.status.in_([MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.EXPIRED]),
                Mission.updated_at < cutoff_date
            )
        )
        cleanup_stats["old_missions"] = old_missions_result.rowcount
        
        # Clean up old inactive game events (older than 7 days)
        event_cutoff = datetime.utcnow() - timedelta(days=7)
        
        old_events_result = await db.execute(
            delete(GameEvent).where(
                GameEvent.is_active == False,
                GameEvent.created_at < event_cutoff
            )
        )
        cleanup_stats["old_events"] = old_events_result.rowcount
        
        # Clean up old combat logs (older than 90 days, keep recent for statistics)
        combat_cutoff = datetime.utcnow() - timedelta(days=90)
        
        old_combat_result = await db.execute(
            delete(CombatLog).where(CombatLog.created_at < combat_cutoff)
        )
        cleanup_stats["old_combat_logs"] = old_combat_result.rowcount
        
        # Clean up old price history from market prices
        result = await db.execute(select(MarketPrice))
        market_prices = result.scalars().all()
        
        price_history_cleaned = 0
        for price in market_prices:
            if price.price_history:
                # Keep only last 7 days of price history
                history_cutoff = datetime.utcnow() - timedelta(days=7)
                old_history = price.price_history.copy()
                
                price.price_history = {
                    timestamp: data
                    for timestamp, data in price.price_history.items()
                    if datetime.fromisoformat(timestamp) > history_cutoff
                }
                
                if len(price.price_history) < len(old_history):
                    price_history_cleaned += 1
        
        cleanup_stats["old_price_history"] = price_history_cleaned
        
        await db.commit()
        
        # Log cleanup results
        await aws_services.s3.upload_game_log({
            "cleanup_type": "scheduled_cleanup",
            "cleanup_stats": cleanup_stats,
            "timestamp": datetime.utcnow().isoformat()
        }, "maintenance")
        
        # Send metrics
        for metric_name, count in cleanup_stats.items():
            await aws_services.cloudwatch.put_metric(f"CleanedUp_{metric_name}", count)
        
        return cleanup_stats


@celery_app.task
def backup_player_data():
    """Backup critical player data to S3."""
    try:
        import asyncio
        return asyncio.run(_backup_player_data_async())
    except Exception as e:
        logger.error(f"Failed to backup player data: {e}")
        return {"error": str(e)}


async def _backup_player_data_async():
    """Async player data backup."""
    async with AsyncSessionLocal() as db:
        # Get all players with their related data
        result = await db.execute(
            select(Player)
            .options(
                selectinload(Player.vehicles),
                selectinload(Player.missions),
                selectinload(Player.faction)
            )
        )
        players = result.scalars().all()
        
        backup_count = 0
        
        for player in players:
            # Create backup data structure
            backup_data = {
                "player_id": player.id,
                "username": player.username,
                "email": player.email,
                "level": player.level,
                "experience": player.experience,
                "credits": player.credits,
                "reputation": player.reputation,
                "faction_id": player.faction_id,
                "current_location_id": player.current_location_id,
                "created_at": player.created_at.isoformat(),
                "last_active": player.last_active.isoformat(),
                "vehicles": [
                    {
                        "id": vehicle.id,
                        "name": vehicle.name,
                        "vehicle_type": vehicle.vehicle_type.value,
                        "speed": vehicle.speed,
                        "cargo_capacity": vehicle.cargo_capacity,
                        "current_fuel": vehicle.current_fuel,
                        "durability": vehicle.durability,
                        "current_location_id": vehicle.current_location_id,
                        "current_cargo": vehicle.current_cargo,
                        "upgrades": vehicle.upgrades
                    }
                    for vehicle in player.vehicles
                ],
                "active_missions": [
                    {
                        "id": mission.id,
                        "title": mission.title,
                        "status": mission.status.value,
                        "origin_id": mission.origin_id,
                        "destination_id": mission.destination_id,
                        "reward_credits": mission.reward_credits,
                        "accepted_at": mission.accepted_at.isoformat() if mission.accepted_at else None
                    }
                    for mission in player.missions
                    if mission.status in [MissionStatus.ACCEPTED, MissionStatus.IN_PROGRESS]
                ],
                "backup_timestamp": datetime.utcnow().isoformat()
            }
            
            # Upload to S3
            backup_url = await aws_services.s3.upload_player_data_backup(player.id, backup_data)
            if backup_url:
                backup_count += 1
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("PlayerDataBackups", backup_count)
        
        return {
            "players_backed_up": backup_count,
            "total_players": len(players)
        }


@celery_app.task
def send_daily_metrics():
    """Send daily game metrics to CloudWatch."""
    try:
        import asyncio
        return asyncio.run(_send_daily_metrics_async())
    except Exception as e:
        logger.error(f"Failed to send daily metrics: {e}")
        return {"error": str(e)}


async def _send_daily_metrics_async():
    """Async daily metrics collection and sending."""
    async with AsyncSessionLocal() as db:
        # Calculate daily metrics
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        # Player metrics
        total_players_result = await db.execute(select(func.count(Player.id)))
        total_players = total_players_result.scalar()
        
        new_players_result = await db.execute(
            select(func.count(Player.id)).where(
                func.date(Player.created_at) == yesterday
            )
        )
        new_players_yesterday = new_players_result.scalar()
        
        active_players_result = await db.execute(
            select(func.count(Player.id)).where(
                func.date(Player.last_active) == yesterday
            )
        )
        active_players_yesterday = active_players_result.scalar()
        
        # Mission metrics
        missions_completed_result = await db.execute(
            select(func.count(Mission.id)).where(
                Mission.status == MissionStatus.COMPLETED,
                func.date(Mission.completed_at) == yesterday
            )
        )
        missions_completed_yesterday = missions_completed_result.scalar()
        
        missions_failed_result = await db.execute(
            select(func.count(Mission.id)).where(
                Mission.status == MissionStatus.FAILED,
                func.date(Mission.updated_at) == yesterday
            )
        )
        missions_failed_yesterday = missions_failed_result.scalar()
        
        # Combat metrics
        combats_yesterday_result = await db.execute(
            select(func.count(CombatLog.id)).where(
                func.date(CombatLog.created_at) == yesterday
            )
        )
        combats_yesterday = combats_yesterday_result.scalar()
        
        # Vehicle metrics
        total_vehicles_result = await db.execute(select(func.count(Vehicle.id)))
        total_vehicles = total_vehicles_result.scalar()
        
        # Economic metrics
        total_credits_result = await db.execute(select(func.sum(Player.credits)))
        total_credits_in_economy = total_credits_result.scalar() or 0
        
        avg_credits_result = await db.execute(select(func.avg(Player.credits)))
        avg_credits_per_player = avg_credits_result.scalar() or 0
        
        # Compile metrics
        daily_metrics = {
            # Player metrics
            "TotalPlayers": total_players,
            "NewPlayersYesterday": new_players_yesterday,
            "ActivePlayersYesterday": active_players_yesterday,
            
            # Mission metrics
            "MissionsCompletedYesterday": missions_completed_yesterday,
            "MissionsFailedYesterday": missions_failed_yesterday,
            
            # Combat metrics
            "CombatsYesterday": combats_yesterday,
            
            # Vehicle metrics
            "TotalVehicles": total_vehicles,
            
            # Economic metrics
            "TotalCreditsInEconomy": float(total_credits_in_economy),
            "AverageCreditsPerPlayer": float(avg_credits_per_player),
            
            # Calculated metrics
            "PlayerRetentionRate": (active_players_yesterday / max(total_players, 1)) * 100,
            "MissionSuccessRate": (missions_completed_yesterday / max(missions_completed_yesterday + missions_failed_yesterday, 1)) * 100,
            "VehiclesPerPlayer": total_vehicles / max(total_players, 1)
        }
        
        # Send to CloudWatch
        await aws_services.cloudwatch.put_game_metrics(daily_metrics)
        
        # Store detailed metrics in S3
        detailed_metrics = {
            "date": yesterday.isoformat(),
            "metrics": daily_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await aws_services.s3.upload_game_log(detailed_metrics, "daily_metrics")
        
        return {
            "metrics_sent": len(daily_metrics),
            "date": yesterday.isoformat(),
            "key_metrics": {
                "total_players": total_players,
                "active_yesterday": active_players_yesterday,
                "missions_completed": missions_completed_yesterday,
                "combats": combats_yesterday
            }
        }


@celery_app.task
def optimize_database():
    """Perform database optimization tasks."""
    try:
        import asyncio
        return asyncio.run(_optimize_database_async())
    except Exception as e:
        logger.error(f"Failed to optimize database: {e}")
        return {"error": str(e)}


async def _optimize_database_async():
    """Async database optimization."""
    async with AsyncSessionLocal() as db:
        optimization_results = {}
        
        # Update player statistics that might be cached
        result = await db.execute(select(Player))
        players = result.scalars().all()
        
        updated_players = 0
        for player in players:
            # Recalculate level based on experience
            correct_level = 1
            remaining_exp = player.experience
            
            while remaining_exp >= (correct_level * 1000):
                remaining_exp -= (correct_level * 1000)
                correct_level += 1
            
            if player.level != correct_level:
                player.level = correct_level
                player.experience = remaining_exp
                updated_players += 1
        
        optimization_results["players_level_corrected"] = updated_players
        
        # Clean up orphaned data
        # Remove vehicles without owners
        orphaned_vehicles_result = await db.execute(
            delete(Vehicle).where(
                ~Vehicle.owner_id.in_(select(Player.id))
            )
        )
        optimization_results["orphaned_vehicles_removed"] = orphaned_vehicles_result.rowcount
        
        # Remove missions without valid locations
        orphaned_missions_result = await db.execute(
            delete(Mission).where(
                ~Mission.origin_id.in_(select(Location.id))
            )
        )
        optimization_results["orphaned_missions_removed"] = orphaned_missions_result.rowcount
        
        await db.commit()
        
        # Log optimization results
        await aws_services.s3.upload_game_log({
            "optimization_type": "database_optimization",
            "results": optimization_results,
            "timestamp": datetime.utcnow().isoformat()
        }, "maintenance")
        
        # Send metrics
        for metric_name, count in optimization_results.items():
            await aws_services.cloudwatch.put_metric(f"DatabaseOptimization_{metric_name}", count)
        
        return optimization_results


@celery_app.task
def health_check_services():
    """Perform health checks on all services."""
    try:
        import asyncio
        return asyncio.run(_health_check_services_async())
    except Exception as e:
        logger.error(f"Failed to perform health check: {e}")
        return {"error": str(e)}


async def _health_check_services_async():
    """Async service health checks."""
    health_status = {}
    
    # Check database connectivity
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(func.count(Player.id)))
            player_count = result.scalar()
            health_status["database"] = {
                "status": "healthy",
                "player_count": player_count
            }
    except Exception as e:
        health_status["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check AWS services
    aws_health = await aws_services.health_check()
    health_status["aws_services"] = aws_health
    
    # Check Redis (via Celery broker)
    try:
        import redis
        from ..config import settings
        
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        health_status["redis"] = {"status": "healthy"}
    except Exception as e:
        health_status["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Overall health status
    all_healthy = all(
        service.get("status") == "healthy" or 
        (isinstance(service, dict) and all(v for v in service.values()))
        for service in health_status.values()
    )
    
    health_status["overall"] = {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Log health check results
    await aws_services.s3.upload_game_log({
        "health_check": health_status,
        "timestamp": datetime.utcnow().isoformat()
    }, "health_checks")
    
    # Send health metrics
    await aws_services.cloudwatch.put_metric(
        "ServiceHealthCheck", 
        1 if all_healthy else 0
    )
    
    return health_status

from ..models import Location
