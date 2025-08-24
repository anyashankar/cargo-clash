"""Authentication and authorization utilities."""

import os
from datetime import datetime, timedelta
from typing import Optional

import boto3
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pycognito import Cognito
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .config import settings
from .database import get_async_db
from .models import Player

security = HTTPBearer()


class CognitoAuth:
    """AWS Cognito authentication handler."""
    
    def __init__(self):
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.client_secret = settings.cognito_client_secret
        self.region = settings.aws_region
        
        # Initialize Cognito client
        if self.user_pool_id and self.client_id:
            self.cognito = Cognito(
                user_pool_id=self.user_pool_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_pool_region=self.region
            )
        else:
            self.cognito = None
    
    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user with Cognito."""
        if not self.cognito:
            # Fallback to local authentication for development
            return await self._local_auth(username, password)
        
        try:
            self.cognito.authenticate(password=password)
            user_info = self.cognito.get_user()
            return {
                "sub": user_info.sub,
                "username": user_info.username,
                "email": user_info.email,
                "email_verified": user_info.email_verified
            }
        except Exception as e:
            print(f"Cognito authentication failed: {e}")
            return None
    
    async def _local_auth(self, username: str, password: str) -> Optional[dict]:
        """Local authentication fallback for development."""
        # This is a simple fallback - in production, always use Cognito
        if username and password:
            return {
                "sub": f"local_{username}",
                "username": username,
                "email": f"{username}@example.com",
                "email_verified": True
            }
        return None
    
    async def register_user(self, username: str, password: str, email: str) -> Optional[dict]:
        """Register new user with Cognito."""
        if not self.cognito:
            # Fallback for development
            return {
                "sub": f"local_{username}",
                "username": username,
                "email": email,
                "email_verified": False
            }
        
        try:
            self.cognito.register(username, password, email=email)
            return {
                "sub": username,  # Will be updated after confirmation
                "username": username,
                "email": email,
                "email_verified": False
            }
        except Exception as e:
            print(f"Cognito registration failed: {e}")
            return None


cognito_auth = CognitoAuth()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_async_db)
) -> Player:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.secret_key, 
            algorithms=[settings.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(Player).where(Player.cognito_id == username)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    # Update last active timestamp
    user.last_active = datetime.utcnow()
    user.is_online = True
    await db.commit()
    
    return user


async def get_current_active_user(
    current_user: Player = Depends(get_current_user)
) -> Player:
    """Get current active user (additional checks can be added here)."""
    return current_user


class PermissionChecker:
    """Check user permissions for various actions."""
    
    @staticmethod
    def can_access_vehicle(user: Player, vehicle_id: int) -> bool:
        """Check if user can access a specific vehicle."""
        # User can access their own vehicles
        return any(v.id == vehicle_id for v in user.vehicles)
    
    @staticmethod
    def can_accept_mission(user: Player, mission) -> bool:
        """Check if user can accept a mission."""
        # Check level requirement
        if user.level < mission.min_level:
            return False
        
        # Check reputation requirement
        if user.reputation < mission.required_reputation:
            return False
        
        # Check if user has required vehicle type
        if mission.required_vehicle_type:
            has_vehicle = any(
                v.vehicle_type == mission.required_vehicle_type 
                for v in user.vehicles
            )
            if not has_vehicle:
                return False
        
        return True
    
    @staticmethod
    def can_attack_player(attacker: Player, target: Player) -> bool:
        """Check if player can attack another player."""
        # Basic PvP rules - can be expanded
        if attacker.id == target.id:
            return False
        
        # Check if players are in same faction (no friendly fire)
        if attacker.faction_id and attacker.faction_id == target.faction_id:
            return False
        
        return True


permission_checker = PermissionChecker()
