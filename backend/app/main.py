"""Main FastAPI application for Cargo Clash."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response

from .config import settings
from .database import init_db
from .routers import auth, players, vehicles, missions, locations, market, combat, alliances
from .websocket_manager import WebSocketManager
from .game_engine import GameEngine

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# WebSocket manager and game engine
websocket_manager = WebSocketManager()
game_engine = GameEngine(websocket_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Cargo Clash server...")
    await init_db()
    
    # Start game engine
    game_task = asyncio.create_task(game_engine.start())
    
    logger.info("Cargo Clash server started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cargo Clash server...")
    game_task.cancel()
    try:
        await game_task
    except asyncio.CancelledError:
        pass
    
    await game_engine.stop()
    logger.info("Cargo Clash server stopped.")


# Create FastAPI app
app = FastAPI(
    title="Cargo Clash API",
    description="A dynamic multiplayer cargo transportation game",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type="text/plain")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "game_engine_running": game_engine.is_running
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(players.router, prefix="/api/players", tags=["players"])
app.include_router(vehicles.router, prefix="/api/vehicles", tags=["vehicles"])
app.include_router(missions.router, prefix="/api/missions", tags=["missions"])
app.include_router(locations.router, prefix="/api/locations", tags=["locations"])
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(combat.router, prefix="/api/combat", tags=["combat"])
app.include_router(alliances.router, prefix="/api/alliances", tags=["alliances"])


# WebSocket endpoint
@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: int):
    """WebSocket endpoint for real-time game updates."""
    await websocket_manager.connect(websocket, player_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            # Process game actions
            await game_engine.process_player_action(player_id, data)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(player_id)
    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {e}")
        await websocket_manager.disconnect(player_id)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Cargo Clash API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }
