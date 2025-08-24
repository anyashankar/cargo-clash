"""Location management routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..database import get_async_db
from ..models import Player, Location
from ..schemas import LocationResponse, LocationCreate

router = APIRouter()


@router.get("/", response_model=List[LocationResponse])
async def get_locations(
    skip: int = 0,
    limit: int = 100,
    region: Optional[str] = None,
    location_type: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db)
):
    """Get list of locations."""
    query = select(Location).where(Location.is_active == True)
    
    if region:
        query = query.where(Location.region == region)
    
    if location_type:
        query = query.where(Location.location_type == location_type)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    locations = result.scalars().all()
    
    return locations


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get specific location details."""
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.controlling_faction))
        .where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    return location


@router.post("/", response_model=LocationResponse)
async def create_location(
    location_data: LocationCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Create a new location (admin function)."""
    # In a real game, this would be restricted to admins
    
    # Check if location name already exists
    result = await db.execute(
        select(Location).where(Location.name == location_data.name)
    )
    existing_location = result.scalar_one_or_none()
    
    if existing_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location with this name already exists"
        )
    
    # Create location
    new_location = Location(
        name=location_data.name,
        location_type=location_data.location_type,
        x_coordinate=location_data.x_coordinate,
        y_coordinate=location_data.y_coordinate,
        region=location_data.region,
        danger_level=location_data.danger_level,
        population=location_data.population,
        prosperity=location_data.prosperity
    )
    
    # Initialize market data with default prices
    default_market_data = {
        "food": {"buy": 10, "sell": 15, "supply": 100, "demand": 100},
        "fuel": {"buy": 20, "sell": 25, "supply": 100, "demand": 100},
        "electronics": {"buy": 100, "sell": 150, "supply": 50, "demand": 75},
        "weapons": {"buy": 500, "sell": 750, "supply": 20, "demand": 30},
        "artifacts": {"buy": 1000, "sell": 1500, "supply": 5, "demand": 10},
        "materials": {"buy": 50, "sell": 75, "supply": 80, "demand": 90}
    }
    new_location.market_data = default_market_data
    
    db.add(new_location)
    await db.commit()
    await db.refresh(new_location)
    
    return new_location


@router.get("/{location_id}/nearby", response_model=List[LocationResponse])
async def get_nearby_locations(
    location_id: int,
    radius: float = 100.0,
    db: AsyncSession = Depends(get_async_db)
):
    """Get locations within specified radius."""
    # Get the reference location
    result = await db.execute(
        select(Location).where(Location.id == location_id)
    )
    reference_location = result.scalar_one_or_none()
    
    if not reference_location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference location not found"
        )
    
    # Get all locations
    result = await db.execute(
        select(Location).where(Location.is_active == True)
    )
    all_locations = result.scalars().all()
    
    # Filter by distance
    nearby_locations = []
    for location in all_locations:
        if location.id == location_id:
            continue
        
        # Calculate distance
        distance = ((location.x_coordinate - reference_location.x_coordinate) ** 2 + 
                   (location.y_coordinate - reference_location.y_coordinate) ** 2) ** 0.5
        
        if distance <= radius:
            nearby_locations.append(location)
    
    # Sort by distance
    nearby_locations.sort(
        key=lambda loc: ((loc.x_coordinate - reference_location.x_coordinate) ** 2 + 
                        (loc.y_coordinate - reference_location.y_coordinate) ** 2) ** 0.5
    )
    
    return nearby_locations


@router.get("/{location_id}/players")
async def get_players_at_location(
    location_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get players currently at this location."""
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
    
    # Get players at this location
    result = await db.execute(
        select(Player).where(
            Player.current_location_id == location_id,
            Player.is_online == True
        )
    )
    players = result.scalars().all()
    
    # Return basic player info (not full profiles for privacy)
    return [
        {
            "id": player.id,
            "username": player.username,
            "level": player.level,
            "reputation": player.reputation,
            "faction_id": player.faction_id
        }
        for player in players
    ]


@router.get("/regions/list")
async def get_regions(
    db: AsyncSession = Depends(get_async_db)
):
    """Get list of all regions."""
    result = await db.execute(
        select(Location.region).distinct()
    )
    regions = [row[0] for row in result.all()]
    
    return {"regions": regions}


@router.get("/types/list")
async def get_location_types(
    db: AsyncSession = Depends(get_async_db)
):
    """Get list of all location types."""
    result = await db.execute(
        select(Location.location_type).distinct()
    )
    location_types = [row[0] for row in result.all()]
    
    return {"location_types": location_types}
