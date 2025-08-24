"""Player management routes."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..database import get_async_db
from ..models import Player
from ..schemas import PlayerResponse, PlayerUpdate, PlayerStats, Leaderboard, LeaderboardEntry

router = APIRouter()


@router.get("/", response_model=List[PlayerResponse])
async def get_players(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    """Get list of players."""
    result = await db.execute(
        select(Player)
        .options(selectinload(Player.vehicles))
        .offset(skip)
        .limit(limit)
    )
    players = result.scalars().all()
    return players


@router.get("/me", response_model=PlayerResponse)
async def get_my_profile(
    current_user: Player = Depends(get_current_user)
):
    """Get current player's profile."""
    return current_user


@router.put("/me", response_model=PlayerResponse)
async def update_my_profile(
    player_update: PlayerUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Update current player's profile."""
    # Update fields if provided
    if player_update.username is not None:
        # Check if username is already taken
        result = await db.execute(
            select(Player).where(
                Player.username == player_update.username,
                Player.id != current_user.id
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        current_user.username = player_update.username
    
    if player_update.email is not None:
        # Check if email is already taken
        result = await db.execute(
            select(Player).where(
                Player.email == player_update.email,
                Player.id != current_user.id
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
        
        current_user.email = player_update.email
    
    await db.commit()
    await db.refresh(current_user)
    
    return current_user


@router.get("/{player_id}", response_model=PlayerResponse)
async def get_player(
    player_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get specific player by ID."""
    result = await db.execute(
        select(Player)
        .options(selectinload(Player.vehicles))
        .where(Player.id == player_id)
    )
    player = result.scalar_one_or_none()
    
    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    return player


@router.get("/me/stats", response_model=PlayerStats)
async def get_my_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Get current player's statistics."""
    # This would typically involve complex queries across multiple tables
    # For now, returning mock data - implement actual calculations
    
    return PlayerStats(
        total_missions_completed=len([m for m in current_user.missions if m.status.value == "completed"]),
        total_credits_earned=current_user.credits,
        total_distance_traveled=0.0,  # Calculate from mission history
        total_cargo_delivered=0,  # Calculate from mission history
        combat_wins=len([c for c in current_user.combat_logs if c.winner_id == current_user.id]),
        combat_losses=len([c for c in current_user.combat_logs if c.winner_id != current_user.id]),
        reputation_rank=1  # Calculate rank based on reputation
    )


@router.get("/leaderboard/{category}", response_model=Leaderboard)
async def get_leaderboard(
    category: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_async_db)
):
    """Get leaderboard for specified category."""
    valid_categories = ["credits", "reputation", "level", "missions"]
    
    if category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Must be one of: {valid_categories}"
        )
    
    # Build query based on category
    if category == "credits":
        order_field = Player.credits
    elif category == "reputation":
        order_field = Player.reputation
    elif category == "level":
        order_field = Player.level
    else:  # missions - would need to calculate from missions table
        order_field = Player.experience  # Using experience as proxy
    
    result = await db.execute(
        select(Player)
        .order_by(order_field.desc())
        .limit(limit)
    )
    players = result.scalars().all()
    
    # Create leaderboard entries
    entries = []
    for rank, player in enumerate(players, 1):
        if category == "credits":
            score = player.credits
        elif category == "reputation":
            score = player.reputation
        elif category == "level":
            score = player.level
        else:
            score = player.experience
        
        entries.append(LeaderboardEntry(
            player_id=player.id,
            username=player.username,
            score=score,
            rank=rank
        ))
    
    return Leaderboard(
        category=category,
        entries=entries,
        last_updated=datetime.utcnow()
    )


from datetime import datetime
