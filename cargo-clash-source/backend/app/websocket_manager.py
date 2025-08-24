"""WebSocket connection manager for real-time game updates."""

import json
import logging
from typing import Dict, List, Set, Any
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time game updates."""
    
    def __init__(self):
        # Active connections: player_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        
        # Player locations for proximity-based updates
        self.player_locations: Dict[int, int] = {}  # player_id -> location_id
        
        # Location-based groups for efficient broadcasting
        self.location_groups: Dict[int, Set[int]] = {}  # location_id -> set of player_ids
        
        # Alliance-based groups
        self.alliance_groups: Dict[int, Set[int]] = {}  # alliance_id -> set of player_ids
    
    async def connect(self, websocket: WebSocket, player_id: int):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[player_id] = websocket
        
        logger.info(f"Player {player_id} connected via WebSocket")
        
        # Send welcome message
        await self.send_personal_message(player_id, {
            "type": "connection_established",
            "data": {
                "player_id": player_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to Cargo Clash real-time updates"
            }
        })
    
    async def disconnect(self, player_id: int):
        """Remove a WebSocket connection."""
        if player_id in self.active_connections:
            del self.active_connections[player_id]
        
        # Remove from location groups
        if player_id in self.player_locations:
            location_id = self.player_locations[player_id]
            if location_id in self.location_groups:
                self.location_groups[location_id].discard(player_id)
                if not self.location_groups[location_id]:
                    del self.location_groups[location_id]
            del self.player_locations[player_id]
        
        # Remove from alliance groups
        for alliance_id, members in self.alliance_groups.items():
            members.discard(player_id)
        
        # Clean up empty alliance groups
        self.alliance_groups = {
            alliance_id: members 
            for alliance_id, members in self.alliance_groups.items() 
            if members
        }
        
        logger.info(f"Player {player_id} disconnected from WebSocket")
    
    async def send_personal_message(self, player_id: int, message: Dict[str, Any]):
        """Send a message to a specific player."""
        if player_id in self.active_connections:
            try:
                websocket = self.active_connections[player_id]
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to player {player_id}: {e}")
                await self.disconnect(player_id)
    
    async def broadcast_to_location(self, location_id: int, message: Dict[str, Any], exclude_player: int = None):
        """Broadcast a message to all players at a specific location."""
        if location_id not in self.location_groups:
            return
        
        players_to_notify = self.location_groups[location_id].copy()
        if exclude_player:
            players_to_notify.discard(exclude_player)
        
        for player_id in players_to_notify:
            await self.send_personal_message(player_id, message)
    
    async def broadcast_to_alliance(self, alliance_id: int, message: Dict[str, Any], exclude_player: int = None):
        """Broadcast a message to all members of an alliance."""
        if alliance_id not in self.alliance_groups:
            return
        
        players_to_notify = self.alliance_groups[alliance_id].copy()
        if exclude_player:
            players_to_notify.discard(exclude_player)
        
        for player_id in players_to_notify:
            await self.send_personal_message(player_id, message)
    
    async def broadcast_to_nearby_players(self, center_location_id: int, radius: int, message: Dict[str, Any]):
        """Broadcast to players within a certain radius of a location."""
        # This would require location coordinate calculations
        # For now, just broadcast to the specific location
        await self.broadcast_to_location(center_location_id, message)
    
    async def broadcast_global(self, message: Dict[str, Any]):
        """Broadcast a message to all connected players."""
        disconnected_players = []
        
        for player_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to player {player_id}: {e}")
                disconnected_players.append(player_id)
        
        # Clean up disconnected players
        for player_id in disconnected_players:
            await self.disconnect(player_id)
    
    def update_player_location(self, player_id: int, location_id: int):
        """Update a player's location for proximity-based messaging."""
        # Remove from old location group
        if player_id in self.player_locations:
            old_location_id = self.player_locations[player_id]
            if old_location_id in self.location_groups:
                self.location_groups[old_location_id].discard(player_id)
                if not self.location_groups[old_location_id]:
                    del self.location_groups[old_location_id]
        
        # Add to new location group
        self.player_locations[player_id] = location_id
        if location_id not in self.location_groups:
            self.location_groups[location_id] = set()
        self.location_groups[location_id].add(player_id)
    
    def update_player_alliance(self, player_id: int, alliance_id: int = None, old_alliance_id: int = None):
        """Update a player's alliance membership."""
        # Remove from old alliance group
        if old_alliance_id and old_alliance_id in self.alliance_groups:
            self.alliance_groups[old_alliance_id].discard(player_id)
            if not self.alliance_groups[old_alliance_id]:
                del self.alliance_groups[old_alliance_id]
        
        # Add to new alliance group
        if alliance_id:
            if alliance_id not in self.alliance_groups:
                self.alliance_groups[alliance_id] = set()
            self.alliance_groups[alliance_id].add(player_id)
    
    def get_connected_players(self) -> List[int]:
        """Get list of all connected player IDs."""
        return list(self.active_connections.keys())
    
    def get_players_at_location(self, location_id: int) -> List[int]:
        """Get list of player IDs at a specific location."""
        return list(self.location_groups.get(location_id, set()))
    
    def get_alliance_members_online(self, alliance_id: int) -> List[int]:
        """Get list of online alliance members."""
        return list(self.alliance_groups.get(alliance_id, set()))
    
    def is_player_connected(self, player_id: int) -> bool:
        """Check if a player is currently connected."""
        return player_id in self.active_connections
    
    async def send_game_state_update(self, player_id: int, game_state: Dict[str, Any]):
        """Send a game state update to a player."""
        message = {
            "type": "game_state_update",
            "data": game_state,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(player_id, message)
    
    async def send_market_update(self, location_id: int, market_data: Dict[str, Any]):
        """Send market price updates to players at a location."""
        message = {
            "type": "market_update",
            "data": {
                "location_id": location_id,
                "market_data": market_data
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_location(location_id, message)
    
    async def send_combat_update(self, participants: List[int], combat_data: Dict[str, Any]):
        """Send combat updates to participants and nearby players."""
        message = {
            "type": "combat_update",
            "data": combat_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to all participants
        for player_id in participants:
            await self.send_personal_message(player_id, message)
        
        # Also send to nearby players if location is specified
        if "location_id" in combat_data:
            await self.broadcast_to_location(
                combat_data["location_id"], 
                message, 
                exclude_player=None
            )
    
    async def send_mission_update(self, player_id: int, mission_data: Dict[str, Any]):
        """Send mission updates to a player."""
        message = {
            "type": "mission_update",
            "data": mission_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(player_id, message)
    
    async def send_alliance_update(self, alliance_id: int, update_data: Dict[str, Any]):
        """Send alliance updates to all members."""
        message = {
            "type": "alliance_update",
            "data": update_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_alliance(alliance_id, message)
    
    async def send_world_event(self, event_data: Dict[str, Any], affected_locations: List[int] = None):
        """Send world event notifications."""
        message = {
            "type": "world_event",
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if affected_locations:
            # Send to players at affected locations
            for location_id in affected_locations:
                await self.broadcast_to_location(location_id, message)
        else:
            # Global event - send to all players
            await self.broadcast_global(message)
    
    async def send_player_notification(self, player_id: int, notification: Dict[str, Any]):
        """Send a notification to a specific player."""
        message = {
            "type": "notification",
            "data": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_personal_message(player_id, message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about current connections."""
        return {
            "total_connections": len(self.active_connections),
            "location_groups": len(self.location_groups),
            "alliance_groups": len(self.alliance_groups),
            "players_by_location": {
                location_id: len(players) 
                for location_id, players in self.location_groups.items()
            },
            "players_by_alliance": {
                alliance_id: len(players) 
                for alliance_id, players in self.alliance_groups.items()
            }
        }
