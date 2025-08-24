"""Authentication routes."""

from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..auth import cognito_auth, create_access_token, get_current_user
from ..config import settings
from ..database import get_async_db
from ..models import Player
from ..schemas import UserLogin, UserRegister, Token, PlayerResponse

router = APIRouter()


@router.post("/register", response_model=Dict[str, Any])
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_async_db)
):
    """Register a new user."""
    # Check if username already exists
    result = await db.execute(
        select(Player).where(Player.username == user_data.username)
    )
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    result = await db.execute(
        select(Player).where(Player.email == user_data.email)
    )
    existing_email = result.scalar_one_or_none()
    
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Register with Cognito
    cognito_user = await cognito_auth.register_user(
        user_data.username,
        user_data.password,
        user_data.email
    )
    
    if not cognito_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed"
        )
    
    # Create player in database
    new_player = Player(
        cognito_id=cognito_user["sub"],
        username=user_data.username,
        email=user_data.email
    )
    
    db.add(new_player)
    await db.commit()
    await db.refresh(new_player)
    
    return {
        "message": "User registered successfully",
        "user_id": new_player.id,
        "email_verified": cognito_user.get("email_verified", False)
    }


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_async_db)
):
    """Authenticate user and return access token."""
    # Authenticate with Cognito
    cognito_user = await cognito_auth.authenticate_user(
        user_credentials.username,
        user_credentials.password
    )
    
    if not cognito_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get or create player in database
    result = await db.execute(
        select(Player).where(Player.cognito_id == cognito_user["sub"])
    )
    player = result.scalar_one_or_none()
    
    if not player:
        # Create player if doesn't exist (for existing Cognito users)
        player = Player(
            cognito_id=cognito_user["sub"],
            username=cognito_user["username"],
            email=cognito_user["email"]
        )
        db.add(player)
        await db.commit()
        await db.refresh(player)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": cognito_user["sub"]},
        expires_delta=access_token_expires
    )
    
    # Update player status
    player.is_online = True
    await db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/logout")
async def logout(
    db: AsyncSession = Depends(get_async_db),
    current_user: Player = Depends(get_current_user)
):
    """Logout user."""
    # Update player status
    current_user.is_online = False
    await db.commit()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=PlayerResponse)
async def get_current_user_info(
    current_user: Player = Depends(get_current_user)
):
    """Get current user information."""
    return current_user


# Import get_current_user here to avoid circular imports
from ..auth import get_current_user
