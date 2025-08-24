"""Market-related Celery tasks."""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..celery_app import celery_app
from ..database import AsyncSessionLocal
from ..models import MarketPrice, Location, CargoType, GameEvent, GameEventType
from ..aws_services import aws_services

logger = logging.getLogger(__name__)


@celery_app.task
def update_market_prices():
    """Update market prices across all locations."""
    try:
        import asyncio
        return asyncio.run(_update_market_prices_async())
    except Exception as e:
        logger.error(f"Failed to update market prices: {e}")
        return {"error": str(e)}


async def _update_market_prices_async():
    """Async market price updates."""
    async with AsyncSessionLocal() as db:
        # Get all market prices
        result = await db.execute(
            select(MarketPrice).options(selectinload(MarketPrice.location))
        )
        market_prices = result.scalars().all()
        
        updated_count = 0
        price_changes = {}
        
        for price in market_prices:
            old_buy_price = price.buy_price
            old_sell_price = price.sell_price
            
            # Apply market fluctuations
            price_change = await _calculate_price_change(price, db)
            
            if price_change["buy_change"] != 0 or price_change["sell_change"] != 0:
                price.buy_price = max(1, price.buy_price + price_change["buy_change"])
                price.sell_price = max(1, price.sell_price + price_change["sell_change"])
                
                # Update supply and demand
                price.supply = max(0, price.supply + price_change["supply_change"])
                price.demand = max(0, price.demand + price_change["demand_change"])
                
                # Update price history
                if not price.price_history:
                    price.price_history = {}
                
                current_time = datetime.utcnow()
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
                
                updated_count += 1
                
                # Track significant price changes
                buy_change_percent = abs(price_change["buy_change"]) / max(old_buy_price, 1)
                sell_change_percent = abs(price_change["sell_change"]) / max(old_sell_price, 1)
                
                if buy_change_percent > 0.1 or sell_change_percent > 0.1:  # 10% change
                    location_key = f"{price.location_id}_{price.cargo_type.value}"
                    price_changes[location_key] = {
                        "location_id": price.location_id,
                        "location_name": price.location.name,
                        "cargo_type": price.cargo_type.value,
                        "old_buy_price": old_buy_price,
                        "new_buy_price": price.buy_price,
                        "old_sell_price": old_sell_price,
                        "new_sell_price": price.sell_price,
                        "buy_change_percent": round(buy_change_percent * 100, 2),
                        "sell_change_percent": round(sell_change_percent * 100, 2)
                    }
        
        await db.commit()
        
        # Send significant price changes to SQS for real-time updates
        if price_changes:
            await aws_services.sqs.send_game_event("market_price_changes", {
                "changes": list(price_changes.values()),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("MarketPricesUpdated", updated_count)
        await aws_services.cloudwatch.put_metric("SignificantPriceChanges", len(price_changes))
        
        return {
            "updated_prices": updated_count,
            "significant_changes": len(price_changes),
            "changes": list(price_changes.values())
        }


async def _calculate_price_change(price: MarketPrice, db) -> Dict[str, int]:
    """Calculate price changes based on supply, demand, and events."""
    # Base random fluctuation
    base_change = random.randint(-5, 5)
    
    # Supply and demand influence
    supply_demand_ratio = price.supply / max(price.demand, 1)
    
    if supply_demand_ratio > 1.5:
        # Oversupply - prices tend to drop
        price_modifier = random.randint(-10, -2)
    elif supply_demand_ratio < 0.7:
        # High demand - prices tend to rise
        price_modifier = random.randint(2, 10)
    else:
        price_modifier = random.randint(-3, 3)
    
    # Check for active events affecting this location
    result = await db.execute(
        select(GameEvent).where(
            GameEvent.is_active == True,
            GameEvent.affected_locations.contains([price.location_id])
        )
    )
    active_events = result.scalars().all()
    
    event_modifier = 0
    for event in active_events:
        if event.event_type == GameEventType.MARKET_SHIFT:
            event_data = event.event_data or {}
            if event_data.get("cargo_type") == price.cargo_type.value:
                multiplier = event_data.get("price_multiplier", 1.0)
                if multiplier > 1.0:
                    event_modifier += random.randint(5, 15)
                else:
                    event_modifier -= random.randint(5, 15)
    
    # Calculate final changes
    buy_change = base_change + price_modifier + event_modifier
    sell_change = base_change + price_modifier + event_modifier
    
    # Supply and demand changes (opposite to price changes)
    supply_change = random.randint(-10, 10)
    demand_change = random.randint(-10, 10)
    
    # If prices are rising, supply tends to increase and demand decrease
    if buy_change > 0:
        supply_change += random.randint(0, 5)
        demand_change -= random.randint(0, 3)
    elif buy_change < 0:
        supply_change -= random.randint(0, 3)
        demand_change += random.randint(0, 5)
    
    return {
        "buy_change": buy_change,
        "sell_change": sell_change,
        "supply_change": supply_change,
        "demand_change": demand_change
    }


@celery_app.task
def analyze_market_trends():
    """Analyze market trends and generate insights."""
    try:
        import asyncio
        return asyncio.run(_analyze_market_trends_async())
    except Exception as e:
        logger.error(f"Failed to analyze market trends: {e}")
        return {"error": str(e)}


async def _analyze_market_trends_async():
    """Async market trend analysis."""
    async with AsyncSessionLocal() as db:
        # Get all market prices with history
        result = await db.execute(
            select(MarketPrice).options(selectinload(MarketPrice.location))
        )
        market_prices = result.scalars().all()
        
        trends = {}
        arbitrage_opportunities = []
        
        for price in market_prices:
            if not price.price_history:
                continue
            
            # Analyze price trend
            history_items = sorted(
                price.price_history.items(),
                key=lambda x: datetime.fromisoformat(x[0])
            )
            
            if len(history_items) >= 3:
                # Calculate trend
                recent_prices = [item[1]["buy_price"] for item in history_items[-3:]]
                if recent_prices[0] < recent_prices[-1]:
                    trend = "rising"
                elif recent_prices[0] > recent_prices[-1]:
                    trend = "falling"
                else:
                    trend = "stable"
                
                # Calculate volatility
                price_changes = []
                for i in range(1, len(recent_prices)):
                    change_percent = abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                    price_changes.append(change_percent)
                
                volatility = sum(price_changes) / len(price_changes) if price_changes else 0
                
                trend_key = f"{price.location_id}_{price.cargo_type.value}"
                trends[trend_key] = {
                    "location_id": price.location_id,
                    "location_name": price.location.name,
                    "cargo_type": price.cargo_type.value,
                    "trend": trend,
                    "volatility": round(volatility * 100, 2),
                    "current_buy_price": price.buy_price,
                    "current_sell_price": price.sell_price,
                    "supply": price.supply,
                    "demand": price.demand
                }
        
        # Find arbitrage opportunities
        cargo_types = list(CargoType)
        for cargo_type in cargo_types:
            cargo_prices = [p for p in market_prices if p.cargo_type == cargo_type]
            
            for buy_price in cargo_prices:
                for sell_price in cargo_prices:
                    if buy_price.location_id == sell_price.location_id:
                        continue
                    
                    # Calculate potential profit
                    profit_per_unit = sell_price.sell_price - buy_price.buy_price
                    profit_margin = profit_per_unit / buy_price.buy_price if buy_price.buy_price > 0 else 0
                    
                    # Only consider profitable opportunities with good supply/demand
                    if (profit_margin > 0.2 and  # 20% profit margin
                        buy_price.supply > 10 and 
                        sell_price.demand > 10):
                        
                        # Calculate distance (simplified)
                        distance = ((sell_price.location.x_coordinate - buy_price.location.x_coordinate) ** 2 + 
                                   (sell_price.location.y_coordinate - buy_price.location.y_coordinate) ** 2) ** 0.5
                        
                        max_quantity = min(buy_price.supply, sell_price.demand)
                        total_profit = profit_per_unit * max_quantity
                        
                        arbitrage_opportunities.append({
                            "cargo_type": cargo_type.value,
                            "buy_location": {
                                "id": buy_price.location_id,
                                "name": buy_price.location.name,
                                "price": buy_price.buy_price,
                                "supply": buy_price.supply
                            },
                            "sell_location": {
                                "id": sell_price.location_id,
                                "name": sell_price.location.name,
                                "price": sell_price.sell_price,
                                "demand": sell_price.demand
                            },
                            "profit_per_unit": profit_per_unit,
                            "profit_margin": round(profit_margin * 100, 2),
                            "max_quantity": max_quantity,
                            "total_profit": total_profit,
                            "distance": round(distance, 2)
                        })
        
        # Sort arbitrage opportunities by profit margin
        arbitrage_opportunities.sort(key=lambda x: x["profit_margin"], reverse=True)
        
        # Send analysis to S3 for storage
        analysis_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "trends": trends,
            "arbitrage_opportunities": arbitrage_opportunities[:20],  # Top 20
            "total_markets_analyzed": len(market_prices),
            "trending_up": len([t for t in trends.values() if t["trend"] == "rising"]),
            "trending_down": len([t for t in trends.values() if t["trend"] == "falling"]),
            "stable_markets": len([t for t in trends.values() if t["trend"] == "stable"])
        }
        
        await aws_services.s3.upload_game_log(analysis_data, "market_analysis")
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("MarketTrendsAnalyzed", len(trends))
        await aws_services.cloudwatch.put_metric("ArbitrageOpportunities", len(arbitrage_opportunities))
        
        return {
            "trends_analyzed": len(trends),
            "arbitrage_opportunities": len(arbitrage_opportunities),
            "top_opportunities": arbitrage_opportunities[:5]
        }


@celery_app.task
def rebalance_market_supply():
    """Rebalance market supply and demand to prevent extreme imbalances."""
    try:
        import asyncio
        return asyncio.run(_rebalance_market_supply_async())
    except Exception as e:
        logger.error(f"Failed to rebalance market supply: {e}")
        return {"error": str(e)}


async def _rebalance_market_supply_async():
    """Async market rebalancing."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(MarketPrice))
        market_prices = result.scalars().all()
        
        rebalanced_count = 0
        
        for price in market_prices:
            rebalanced = False
            
            # Rebalance extreme supply shortages
            if price.supply < 5:
                price.supply += random.randint(20, 50)
                rebalanced = True
            
            # Rebalance extreme demand shortages
            if price.demand < 5:
                price.demand += random.randint(20, 50)
                rebalanced = True
            
            # Rebalance extreme oversupply
            if price.supply > 500:
                price.supply = random.randint(200, 400)
                rebalanced = True
            
            # Rebalance extreme overdemand
            if price.demand > 500:
                price.demand = random.randint(200, 400)
                rebalanced = True
            
            if rebalanced:
                rebalanced_count += 1
        
        await db.commit()
        
        # Send metrics
        await aws_services.cloudwatch.put_metric("MarketsRebalanced", rebalanced_count)
        
        return {"markets_rebalanced": rebalanced_count}
