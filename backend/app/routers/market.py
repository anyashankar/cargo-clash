"""Market and trading routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..database import get_async_db
from ..models import Player, Location, MarketPrice, Vehicle, CargoType
from ..schemas import MarketPriceResponse, TradeOffer, TradeTransaction

router = APIRouter()


@router.get("/prices", response_model=List[MarketPriceResponse])
async def get_market_prices(
    location_id: Optional[int] = None,
    cargo_type: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get market prices."""
    query = select(MarketPrice).options(selectinload(MarketPrice.location))
    
    if location_id:
        query = query.where(MarketPrice.location_id == location_id)
    
    if cargo_type:
        try:
            cargo_enum = CargoType(cargo_type)
            query = query.where(MarketPrice.cargo_type == cargo_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cargo type"
            )
    
    result = await db.execute(query)
    prices = result.scalars().all()
    
    return prices


@router.get("/prices/{location_id}", response_model=List[MarketPriceResponse])
async def get_location_prices(
    location_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get all market prices for a specific location."""
    # Verify location exists
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # Get prices
    result = await db.execute(
        select(MarketPrice)
        .options(selectinload(MarketPrice.location))
        .where(MarketPrice.location_id == location_id)
    )
    prices = result.scalars().all()
    
    return prices


@router.post("/buy")
async def buy_cargo(
    location_id: int,
    cargo_type: str,
    quantity: int,
    vehicle_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Buy cargo at current location."""
    # Validate cargo type
    try:
        cargo_enum = CargoType(cargo_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cargo type"
        )
    
    # Get vehicle
    result = await db.execute(
        select(Vehicle).where(
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
    
    # Check if vehicle is at the location
    if vehicle.current_location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle must be at the trading location"
        )
    
    # Get market price
    result = await db.execute(
        select(MarketPrice).where(
            MarketPrice.location_id == location_id,
            MarketPrice.cargo_type == cargo_enum
        )
    )
    market_price = result.scalar_one_or_none()
    
    if not market_price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No market data for this cargo type at this location"
        )
    
    # Check supply
    if market_price.supply < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient supply. Available: {market_price.supply}"
        )
    
    # Calculate total cost
    total_cost = market_price.buy_price * quantity
    
    # Check player credits
    if current_user.credits < total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits"
        )
    
    # Check vehicle cargo capacity
    current_cargo = vehicle.current_cargo or {}
    current_total = sum(current_cargo.values())
    
    if current_total + quantity > vehicle.cargo_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient cargo capacity"
        )
    
    # Execute trade
    current_user.credits -= total_cost
    market_price.supply -= quantity
    market_price.demand += quantity // 2  # Buying increases demand slightly
    
    # Update vehicle cargo
    if cargo_type in current_cargo:
        current_cargo[cargo_type] += quantity
    else:
        current_cargo[cargo_type] = quantity
    
    vehicle.current_cargo = current_cargo
    
    await db.commit()
    
    return {
        "message": f"Successfully bought {quantity} units of {cargo_type}",
        "total_cost": total_cost,
        "remaining_credits": current_user.credits,
        "vehicle_cargo": vehicle.current_cargo
    }


@router.post("/sell")
async def sell_cargo(
    location_id: int,
    cargo_type: str,
    quantity: int,
    vehicle_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Sell cargo at current location."""
    # Validate cargo type
    try:
        cargo_enum = CargoType(cargo_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cargo type"
        )
    
    # Get vehicle
    result = await db.execute(
        select(Vehicle).where(
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
    
    # Check if vehicle is at the location
    if vehicle.current_location_id != location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle must be at the trading location"
        )
    
    # Check if vehicle has the cargo
    current_cargo = vehicle.current_cargo or {}
    if cargo_type not in current_cargo or current_cargo[cargo_type] < quantity:
        available = current_cargo.get(cargo_type, 0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient cargo. Available: {available}"
        )
    
    # Get market price
    result = await db.execute(
        select(MarketPrice).where(
            MarketPrice.location_id == location_id,
            MarketPrice.cargo_type == cargo_enum
        )
    )
    market_price = result.scalar_one_or_none()
    
    if not market_price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No market data for this cargo type at this location"
        )
    
    # Check demand
    if market_price.demand < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient demand. Current demand: {market_price.demand}"
        )
    
    # Calculate total earnings
    total_earnings = market_price.sell_price * quantity
    
    # Execute trade
    current_user.credits += total_earnings
    market_price.supply += quantity
    market_price.demand -= quantity
    
    # Update vehicle cargo
    current_cargo[cargo_type] -= quantity
    if current_cargo[cargo_type] == 0:
        del current_cargo[cargo_type]
    
    vehicle.current_cargo = current_cargo
    
    await db.commit()
    
    return {
        "message": f"Successfully sold {quantity} units of {cargo_type}",
        "total_earnings": total_earnings,
        "new_credits": current_user.credits,
        "vehicle_cargo": vehicle.current_cargo
    }


@router.get("/trends/{location_id}")
async def get_market_trends(
    location_id: int,
    cargo_type: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get market price trends for a location."""
    # Verify location exists
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    query = select(MarketPrice).where(MarketPrice.location_id == location_id)
    
    if cargo_type:
        try:
            cargo_enum = CargoType(cargo_type)
            query = query.where(MarketPrice.cargo_type == cargo_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cargo type"
            )
    
    result = await db.execute(query)
    prices = result.scalars().all()
    
    trends = []
    for price in prices:
        # Calculate trend based on supply/demand ratio
        supply_demand_ratio = price.supply / max(price.demand, 1)
        
        if supply_demand_ratio > 1.5:
            trend = "falling"
        elif supply_demand_ratio < 0.7:
            trend = "rising"
        else:
            trend = "stable"
        
        trends.append({
            "cargo_type": price.cargo_type.value,
            "current_buy_price": price.buy_price,
            "current_sell_price": price.sell_price,
            "supply": price.supply,
            "demand": price.demand,
            "trend": trend,
            "supply_demand_ratio": round(supply_demand_ratio, 2),
            "price_history": price.price_history
        })
    
    return {
        "location_id": location_id,
        "location_name": location.name,
        "trends": trends
    }


@router.get("/arbitrage")
async def find_arbitrage_opportunities(
    cargo_type: str,
    max_distance: float = 200.0,
    min_profit_margin: float = 0.2,
    db: AsyncSession = Depends(get_async_db)
):
    """Find arbitrage opportunities for a cargo type."""
    try:
        cargo_enum = CargoType(cargo_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cargo type"
        )
    
    # Get all market prices for this cargo type
    result = await db.execute(
        select(MarketPrice)
        .options(selectinload(MarketPrice.location))
        .where(MarketPrice.cargo_type == cargo_enum)
    )
    prices = result.scalars().all()
    
    opportunities = []
    
    # Compare all location pairs
    for buy_price in prices:
        for sell_price in prices:
            if buy_price.location_id == sell_price.location_id:
                continue
            
            # Calculate distance
            distance = ((sell_price.location.x_coordinate - buy_price.location.x_coordinate) ** 2 + 
                       (sell_price.location.y_coordinate - buy_price.location.y_coordinate) ** 2) ** 0.5
            
            if distance > max_distance:
                continue
            
            # Calculate profit margin
            profit_per_unit = sell_price.sell_price - buy_price.buy_price
            profit_margin = profit_per_unit / buy_price.buy_price
            
            if profit_margin < min_profit_margin:
                continue
            
            # Check supply and demand
            max_quantity = min(buy_price.supply, sell_price.demand)
            
            if max_quantity <= 0:
                continue
            
            opportunities.append({
                "buy_location": {
                    "id": buy_price.location_id,
                    "name": buy_price.location.name,
                    "buy_price": buy_price.buy_price,
                    "supply": buy_price.supply
                },
                "sell_location": {
                    "id": sell_price.location_id,
                    "name": sell_price.location.name,
                    "sell_price": sell_price.sell_price,
                    "demand": sell_price.demand
                },
                "distance": round(distance, 2),
                "profit_per_unit": profit_per_unit,
                "profit_margin": round(profit_margin * 100, 2),
                "max_quantity": max_quantity,
                "total_profit": profit_per_unit * max_quantity
            })
    
    # Sort by profit margin
    opportunities.sort(key=lambda x: x["profit_margin"], reverse=True)
    
    return {
        "cargo_type": cargo_type,
        "opportunities": opportunities[:20]  # Return top 20
    }
