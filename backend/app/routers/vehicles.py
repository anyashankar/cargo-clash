"""Vehicle management routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..auth import get_current_user, permission_checker
from ..database import get_async_db
from ..models import Player, Vehicle, Location
from ..schemas import VehicleResponse, VehicleCreate, VehicleUpdate, TravelRequest, TravelResponse

router = APIRouter()


@router.get("/", response_model=List[VehicleResponse])
async def get_my_vehicles(
    current_user: Player = Depends(get_current_user)
):
    """Get current player's vehicles."""
    return current_user.vehicles


@router.post("/", response_model=VehicleResponse)
async def create_vehicle(
    vehicle_data: VehicleCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Create a new vehicle."""
    # Check if player has enough credits (vehicle costs would be defined elsewhere)
    base_cost = 5000  # Base cost for a vehicle
    
    if current_user.credits < base_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits to purchase vehicle"
        )
    
    # Create vehicle
    new_vehicle = Vehicle(
        owner_id=current_user.id,
        name=vehicle_data.name,
        vehicle_type=vehicle_data.vehicle_type,
        current_location_id=current_user.current_location_id
    )
    
    # Set vehicle stats based on type
    if vehicle_data.vehicle_type.value == "truck":
        new_vehicle.speed = 60
        new_vehicle.cargo_capacity = 150
        new_vehicle.fuel_capacity = 200
    elif vehicle_data.vehicle_type.value == "ship":
        new_vehicle.speed = 40
        new_vehicle.cargo_capacity = 500
        new_vehicle.fuel_capacity = 300
    elif vehicle_data.vehicle_type.value == "plane":
        new_vehicle.speed = 200
        new_vehicle.cargo_capacity = 100
        new_vehicle.fuel_capacity = 400
    elif vehicle_data.vehicle_type.value == "train":
        new_vehicle.speed = 80
        new_vehicle.cargo_capacity = 1000
        new_vehicle.fuel_capacity = 500
    
    new_vehicle.current_fuel = new_vehicle.fuel_capacity
    
    # Deduct credits
    current_user.credits -= base_cost
    
    db.add(new_vehicle)
    await db.commit()
    await db.refresh(new_vehicle)
    
    return new_vehicle


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Get specific vehicle."""
    result = await db.execute(
        select(Vehicle)
        .options(
            selectinload(Vehicle.current_location),
            selectinload(Vehicle.destination),
            selectinload(Vehicle.crew_members)
        )
        .where(Vehicle.id == vehicle_id)
    )
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check permissions
    if not permission_checker.can_access_vehicle(current_user, vehicle_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: int,
    vehicle_update: VehicleUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Update vehicle."""
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id)
    )
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check permissions
    if not permission_checker.can_access_vehicle(current_user, vehicle_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update fields
    if vehicle_update.name is not None:
        vehicle.name = vehicle_update.name
    
    await db.commit()
    await db.refresh(vehicle)
    
    return vehicle


@router.post("/{vehicle_id}/travel", response_model=TravelResponse)
async def start_travel(
    vehicle_id: int,
    travel_request: TravelRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Start vehicle travel to destination."""
    # Get vehicle
    result = await db.execute(
        select(Vehicle)
        .options(selectinload(Vehicle.current_location))
        .where(Vehicle.id == vehicle_id)
    )
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check permissions
    if not permission_checker.can_access_vehicle(current_user, vehicle_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check if vehicle is already traveling
    if vehicle.is_traveling:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is already traveling"
        )
    
    # Get destination
    result = await db.execute(
        select(Location).where(Location.id == travel_request.destination_id)
    )
    destination = result.scalar_one_or_none()
    
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination not found"
        )
    
    # Calculate travel time and fuel cost
    if not vehicle.current_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle has no current location"
        )
    
    # Calculate distance (simple Euclidean distance)
    distance = ((destination.x_coordinate - vehicle.current_location.x_coordinate) ** 2 + 
                (destination.y_coordinate - vehicle.current_location.y_coordinate) ** 2) ** 0.5
    
    # Calculate travel time based on vehicle speed
    travel_time_hours = distance / vehicle.speed
    travel_time_minutes = int(travel_time_hours * 60)
    
    # Calculate fuel cost
    fuel_cost = int(distance * 0.1)  # Simple fuel calculation
    
    # Check if vehicle has enough fuel
    if vehicle.current_fuel < fuel_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient fuel for journey"
        )
    
    # Start travel
    from datetime import datetime, timedelta
    
    vehicle.is_traveling = True
    vehicle.destination_id = destination.id
    vehicle.travel_start_time = datetime.utcnow()
    vehicle.estimated_arrival = datetime.utcnow() + timedelta(minutes=travel_time_minutes)
    vehicle.current_fuel -= fuel_cost
    
    await db.commit()
    
    return TravelResponse(
        success=True,
        message=f"Travel started to {destination.name}",
        estimated_arrival=vehicle.estimated_arrival,
        fuel_cost=fuel_cost
    )


@router.post("/{vehicle_id}/refuel")
async def refuel_vehicle(
    vehicle_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Refuel vehicle."""
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id)
    )
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check permissions
    if not permission_checker.can_access_vehicle(current_user, vehicle_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Calculate refuel cost
    fuel_needed = vehicle.fuel_capacity - vehicle.current_fuel
    fuel_cost = fuel_needed * 2  # 2 credits per fuel unit
    
    if current_user.credits < fuel_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits for refuel"
        )
    
    # Refuel
    vehicle.current_fuel = vehicle.fuel_capacity
    current_user.credits -= fuel_cost
    
    await db.commit()
    
    return {
        "message": "Vehicle refueled successfully",
        "fuel_cost": fuel_cost,
        "current_fuel": vehicle.current_fuel
    }


@router.post("/{vehicle_id}/repair")
async def repair_vehicle(
    vehicle_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Repair vehicle."""
    result = await db.execute(
        select(Vehicle).where(Vehicle.id == vehicle_id)
    )
    vehicle = result.scalar_one_or_none()
    
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    # Check permissions
    if not permission_checker.can_access_vehicle(current_user, vehicle_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Calculate repair cost
    damage = vehicle.max_durability - vehicle.durability
    repair_cost = damage * 5  # 5 credits per durability point
    
    if repair_cost == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle doesn't need repairs"
        )
    
    if current_user.credits < repair_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits for repairs"
        )
    
    # Repair
    vehicle.durability = vehicle.max_durability
    current_user.credits -= repair_cost
    
    await db.commit()
    
    return {
        "message": "Vehicle repaired successfully",
        "repair_cost": repair_cost,
        "current_durability": vehicle.durability
    }
