"""Alliance management routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from ..auth import get_current_user
from ..database import get_async_db
from ..models import Player, Alliance, AllianceMembership
from ..schemas import AllianceResponse, AllianceCreate, AllianceUpdate

router = APIRouter()


@router.get("/", response_model=List[AllianceResponse])
async def get_alliances(
    skip: int = 0,
    limit: int = 50,
    recruiting_only: bool = False,
    db: AsyncSession = Depends(get_async_db)
):
    """Get list of alliances."""
    query = select(Alliance).options(selectinload(Alliance.leader))
    
    if recruiting_only:
        query = query.where(Alliance.is_recruiting == True)
    
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    alliances = result.scalars().all()
    
    return alliances


@router.post("/", response_model=AllianceResponse)
async def create_alliance(
    alliance_data: AllianceCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Create a new alliance."""
    # Check if user is already in an alliance
    result = await db.execute(
        select(AllianceMembership).where(AllianceMembership.player_id == current_user.id)
    )
    existing_membership = result.scalar_one_or_none()
    
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of an alliance"
        )
    
    # Check if alliance name already exists
    result = await db.execute(
        select(Alliance).where(Alliance.name == alliance_data.name)
    )
    existing_alliance = result.scalar_one_or_none()
    
    if existing_alliance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alliance name already exists"
        )
    
    # Check if player has enough credits (alliance creation cost)
    creation_cost = 10000
    if current_user.credits < creation_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits to create alliance"
        )
    
    # Create alliance
    new_alliance = Alliance(
        name=alliance_data.name,
        description=alliance_data.description,
        leader_id=current_user.id,
        total_members=1,
        is_recruiting=alliance_data.is_recruiting,
        min_level_requirement=alliance_data.min_level_requirement
    )
    
    db.add(new_alliance)
    await db.flush()  # Get the alliance ID
    
    # Create membership for the leader
    membership = AllianceMembership(
        alliance_id=new_alliance.id,
        player_id=current_user.id,
        role="leader"
    )
    
    db.add(membership)
    
    # Deduct creation cost
    current_user.credits -= creation_cost
    
    await db.commit()
    await db.refresh(new_alliance)
    
    return new_alliance


@router.get("/{alliance_id}", response_model=AllianceResponse)
async def get_alliance(
    alliance_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get specific alliance details."""
    result = await db.execute(
        select(Alliance)
        .options(selectinload(Alliance.leader))
        .where(Alliance.id == alliance_id)
    )
    alliance = result.scalar_one_or_none()
    
    if not alliance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alliance not found"
        )
    
    return alliance


@router.put("/{alliance_id}", response_model=AllianceResponse)
async def update_alliance(
    alliance_id: int,
    alliance_update: AllianceUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Update alliance (leader only)."""
    # Get alliance
    result = await db.execute(
        select(Alliance).where(Alliance.id == alliance_id)
    )
    alliance = result.scalar_one_or_none()
    
    if not alliance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alliance not found"
        )
    
    # Check if user is the leader
    if alliance.leader_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only alliance leader can update alliance settings"
        )
    
    # Update fields
    if alliance_update.name is not None:
        # Check if new name already exists
        result = await db.execute(
            select(Alliance).where(
                Alliance.name == alliance_update.name,
                Alliance.id != alliance_id
            )
        )
        existing_alliance = result.scalar_one_or_none()
        
        if existing_alliance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Alliance name already exists"
            )
        
        alliance.name = alliance_update.name
    
    if alliance_update.description is not None:
        alliance.description = alliance_update.description
    
    if alliance_update.is_recruiting is not None:
        alliance.is_recruiting = alliance_update.is_recruiting
    
    if alliance_update.min_level_requirement is not None:
        alliance.min_level_requirement = alliance_update.min_level_requirement
    
    await db.commit()
    await db.refresh(alliance)
    
    return alliance


@router.post("/{alliance_id}/join")
async def join_alliance(
    alliance_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Join an alliance."""
    # Check if user is already in an alliance
    result = await db.execute(
        select(AllianceMembership).where(AllianceMembership.player_id == current_user.id)
    )
    existing_membership = result.scalar_one_or_none()
    
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of an alliance"
        )
    
    # Get alliance
    result = await db.execute(
        select(Alliance).where(Alliance.id == alliance_id)
    )
    alliance = result.scalar_one_or_none()
    
    if not alliance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alliance not found"
        )
    
    # Check if alliance is recruiting
    if not alliance.is_recruiting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alliance is not currently recruiting"
        )
    
    # Check level requirement
    if current_user.level < alliance.min_level_requirement:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum level requirement: {alliance.min_level_requirement}"
        )
    
    # Create membership
    membership = AllianceMembership(
        alliance_id=alliance_id,
        player_id=current_user.id,
        role="member"
    )
    
    db.add(membership)
    
    # Update alliance member count
    alliance.total_members += 1
    
    await db.commit()
    
    return {"message": f"Successfully joined {alliance.name}"}


@router.post("/{alliance_id}/leave")
async def leave_alliance(
    alliance_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Leave an alliance."""
    # Get membership
    result = await db.execute(
        select(AllianceMembership).where(
            AllianceMembership.alliance_id == alliance_id,
            AllianceMembership.player_id == current_user.id
        )
    )
    membership = result.scalar_one_or_none()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this alliance"
        )
    
    # Get alliance
    result = await db.execute(
        select(Alliance).where(Alliance.id == alliance_id)
    )
    alliance = result.scalar_one_or_none()
    
    if not alliance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alliance not found"
        )
    
    # Check if user is the leader
    if membership.role == "leader":
        # Check if there are other members
        result = await db.execute(
            select(AllianceMembership).where(
                AllianceMembership.alliance_id == alliance_id,
                AllianceMembership.player_id != current_user.id
            )
        )
        other_members = result.scalars().all()
        
        if other_members:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot leave alliance as leader. Transfer leadership first or disband alliance."
            )
        else:
            # Last member leaving - disband alliance
            await db.delete(alliance)
    
    # Remove membership
    await db.delete(membership)
    
    # Update member count
    if alliance.total_members > 0:
        alliance.total_members -= 1
    
    await db.commit()
    
    return {"message": "Successfully left alliance"}


@router.get("/{alliance_id}/members")
async def get_alliance_members(
    alliance_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """Get alliance members."""
    # Verify alliance exists
    result = await db.execute(
        select(Alliance).where(Alliance.id == alliance_id)
    )
    alliance = result.scalar_one_or_none()
    
    if not alliance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alliance not found"
        )
    
    # Get members
    result = await db.execute(
        select(AllianceMembership, Player)
        .join(Player, AllianceMembership.player_id == Player.id)
        .where(AllianceMembership.alliance_id == alliance_id)
    )
    memberships = result.all()
    
    members = []
    for membership, player in memberships:
        members.append({
            "player_id": player.id,
            "username": player.username,
            "level": player.level,
            "reputation": player.reputation,
            "role": membership.role,
            "joined_at": membership.joined_at,
            "is_online": player.is_online,
            "last_active": player.last_active
        })
    
    return {
        "alliance_id": alliance_id,
        "alliance_name": alliance.name,
        "total_members": len(members),
        "members": members
    }


@router.post("/{alliance_id}/kick/{player_id}")
async def kick_member(
    alliance_id: int,
    player_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Kick a member from alliance (leader/officer only)."""
    # Get alliance
    result = await db.execute(
        select(Alliance).where(Alliance.id == alliance_id)
    )
    alliance = result.scalar_one_or_none()
    
    if not alliance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alliance not found"
        )
    
    # Check if current user has permission
    result = await db.execute(
        select(AllianceMembership).where(
            AllianceMembership.alliance_id == alliance_id,
            AllianceMembership.player_id == current_user.id
        )
    )
    current_membership = result.scalar_one_or_none()
    
    if not current_membership or current_membership.role not in ["leader", "officer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only leaders and officers can kick members"
        )
    
    # Get target membership
    result = await db.execute(
        select(AllianceMembership).where(
            AllianceMembership.alliance_id == alliance_id,
            AllianceMembership.player_id == player_id
        )
    )
    target_membership = result.scalar_one_or_none()
    
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player is not a member of this alliance"
        )
    
    # Cannot kick the leader
    if target_membership.role == "leader":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot kick the alliance leader"
        )
    
    # Officers can only kick regular members
    if current_membership.role == "officer" and target_membership.role == "officer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officers cannot kick other officers"
        )
    
    # Remove membership
    await db.delete(target_membership)
    
    # Update member count
    alliance.total_members = max(0, alliance.total_members - 1)
    
    await db.commit()
    
    return {"message": "Member kicked successfully"}


@router.get("/my/alliance", response_model=Optional[AllianceResponse])
async def get_my_alliance(
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Get current player's alliance."""
    result = await db.execute(
        select(Alliance, AllianceMembership)
        .join(AllianceMembership, Alliance.id == AllianceMembership.alliance_id)
        .where(AllianceMembership.player_id == current_user.id)
    )
    result_row = result.first()
    
    if not result_row:
        return None
    
    alliance, membership = result_row
    
    # Add membership info to alliance response
    alliance_dict = alliance.__dict__.copy()
    alliance_dict["my_role"] = membership.role
    alliance_dict["joined_at"] = membership.joined_at
    
    return alliance_dict
