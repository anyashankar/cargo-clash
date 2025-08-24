"""
Load testing script for Cargo Clash using Locust.
Tests API endpoints and WebSocket connections under load.
"""

import json
import random
import time
from locust import HttpUser, task, between
from locust.contrib.fasthttp import FastHttpUser
import websocket
import threading


class CargoClashUser(FastHttpUser):
    """Simulates a Cargo Clash player for load testing."""
    
    wait_time = between(1, 5)
    
    def on_start(self):
        """Setup user session."""
        self.token = None
        self.user_id = None
        self.vehicles = []
        self.missions = []
        self.locations = []
        
        # Register and login
        self.register_and_login()
        
        # Get initial game data
        self.get_initial_data()
    
    def register_and_login(self):
        """Register a new user and login."""
        username = f"testuser_{random.randint(1000, 9999)}"
        email = f"{username}@test.com"
        password = "testpass123"
        
        # Register
        register_data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        with self.client.post("/api/auth/register", json=register_data, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Registration failed: {response.text}")
                return
        
        # Login
        login_data = {
            "username": username,
            "password": password
        }
        
        with self.client.post("/api/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.client.headers.update({"Authorization": f"Bearer {self.token}"})
                response.success()
            else:
                response.failure(f"Login failed: {response.text}")
    
    def get_initial_data(self):
        """Get initial game data."""
        if not self.token:
            return
        
        # Get user profile
        with self.client.get("/api/auth/me", catch_response=True) as response:
            if response.status_code == 200:
                user_data = response.json()
                self.user_id = user_data["id"]
                response.success()
            else:
                response.failure(f"Failed to get user profile: {response.text}")
        
        # Get vehicles
        with self.client.get("/api/vehicles", catch_response=True) as response:
            if response.status_code == 200:
                self.vehicles = response.json()
                response.success()
            else:
                response.failure(f"Failed to get vehicles: {response.text}")
        
        # Get locations
        with self.client.get("/api/locations", catch_response=True) as response:
            if response.status_code == 200:
                self.locations = response.json()
                response.success()
            else:
                response.failure(f"Failed to get locations: {response.text}")
    
    @task(3)
    def get_missions(self):
        """Get available missions."""
        with self.client.get("/api/missions", catch_response=True) as response:
            if response.status_code == 200:
                self.missions = response.json()
                response.success()
            else:
                response.failure(f"Failed to get missions: {response.text}")
    
    @task(2)
    def get_my_missions(self):
        """Get user's missions."""
        with self.client.get("/api/missions/my", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get my missions: {response.text}")
    
    @task(2)
    def get_market_prices(self):
        """Get market prices."""
        if self.locations:
            location_id = random.choice(self.locations)["id"]
            with self.client.get(f"/api/market/prices/{location_id}", catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Failed to get market prices: {response.text}")
    
    @task(1)
    def create_vehicle(self):
        """Create a new vehicle."""
        vehicle_types = ["truck", "ship", "plane", "train"]
        vehicle_data = {
            "name": f"Vehicle_{random.randint(1000, 9999)}",
            "vehicle_type": random.choice(vehicle_types)
        }
        
        with self.client.post("/api/vehicles", json=vehicle_data, catch_response=True) as response:
            if response.status_code == 200:
                new_vehicle = response.json()
                self.vehicles.append(new_vehicle)
                response.success()
            elif response.status_code == 400:
                # Insufficient credits is expected
                response.success()
            else:
                response.failure(f"Failed to create vehicle: {response.text}")
    
    @task(1)
    def accept_mission(self):
        """Accept a mission."""
        if self.missions and self.vehicles:
            mission = random.choice(self.missions)
            vehicle = random.choice(self.vehicles)
            
            with self.client.post(
                f"/api/missions/{mission['id']}/accept",
                json={"vehicle_id": vehicle["id"]},
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code in [400, 403, 404]:
                    # Mission might be taken or requirements not met
                    response.success()
                else:
                    response.failure(f"Failed to accept mission: {response.text}")
    
    @task(1)
    def get_player_stats(self):
        """Get player statistics."""
        with self.client.get("/api/players/me/stats", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get player stats: {response.text}")
    
    @task(1)
    def get_leaderboard(self):
        """Get leaderboard."""
        categories = ["credits", "reputation", "level"]
        category = random.choice(categories)
        
        with self.client.get(f"/api/players/leaderboard/{category}", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get leaderboard: {response.text}")
    
    @task(1)
    def refuel_vehicle(self):
        """Refuel a vehicle."""
        if self.vehicles:
            vehicle = random.choice(self.vehicles)
            
            with self.client.post(f"/api/vehicles/{vehicle['id']}/refuel", catch_response=True) as response:
                if response.status_code == 200:
                    response.success()
                elif response.status_code == 400:
                    # Insufficient credits or already full
                    response.success()
                else:
                    response.failure(f"Failed to refuel vehicle: {response.text}")


class WebSocketUser(HttpUser):
    """Test WebSocket connections."""
    
    wait_time = between(5, 15)
    
    def on_start(self):
        """Setup WebSocket connection."""
        self.ws = None
        self.user_id = random.randint(1, 1000)  # Simulate existing user
        self.connect_websocket()
    
    def connect_websocket(self):
        """Connect to WebSocket."""
        try:
            ws_url = f"ws://localhost:8000/ws/{self.user_id}"
            self.ws = websocket.create_connection(ws_url)
            
            # Start listening thread
            self.listen_thread = threading.Thread(target=self.listen_messages)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            
        except Exception as e:
            print(f"WebSocket connection failed: {e}")
    
    def listen_messages(self):
        """Listen for WebSocket messages."""
        try:
            while self.ws:
                message = self.ws.recv()
                # Process received message
                data = json.loads(message)
                print(f"Received: {data.get('type', 'unknown')}")
        except Exception as e:
            print(f"WebSocket listen error: {e}")
    
    @task
    def send_ping(self):
        """Send ping message."""
        if self.ws:
            try:
                message = {
                    "type": "ping",
                    "data": {"timestamp": time.time()}
                }
                self.ws.send(json.dumps(message))
            except Exception as e:
                print(f"WebSocket send error: {e}")
                self.connect_websocket()  # Reconnect
    
    @task
    def send_game_state_request(self):
        """Request game state update."""
        if self.ws:
            try:
                message = {
                    "type": "get_game_state",
                    "data": {}
                }
                self.ws.send(json.dumps(message))
            except Exception as e:
                print(f"WebSocket send error: {e}")
    
    def on_stop(self):
        """Cleanup WebSocket connection."""
        if self.ws:
            self.ws.close()


class AdminUser(HttpUser):
    """Simulate admin operations."""
    
    wait_time = between(10, 30)
    
    def on_start(self):
        """Setup admin session."""
        # Admin login would go here
        pass
    
    @task
    def health_check(self):
        """Check application health."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.text}")
    
    @task
    def metrics_check(self):
        """Check metrics endpoint."""
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics check failed: {response.text}")


# Test scenarios
class GameplayScenario(CargoClashUser):
    """Focused gameplay testing."""
    
    @task(5)
    def gameplay_loop(self):
        """Simulate typical gameplay loop."""
        # Get missions
        self.get_missions()
        time.sleep(1)
        
        # Check market
        self.get_market_prices()
        time.sleep(1)
        
        # Accept mission if possible
        if random.random() < 0.3:  # 30% chance
            self.accept_mission()
        
        # Check vehicles
        with self.client.get("/api/vehicles", catch_response=True) as response:
            if response.status_code == 200:
                response.success()


class HighLoadScenario(FastHttpUser):
    """High-frequency requests for stress testing."""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    @task(10)
    def rapid_health_checks(self):
        """Rapid health check requests."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.text}")
    
    @task(5)
    def rapid_api_calls(self):
        """Rapid API calls."""
        endpoints = ["/api/locations", "/api/missions"]
        endpoint = random.choice(endpoints)
        
        with self.client.get(endpoint, catch_response=True) as response:
            if response.status_code in [200, 401]:  # 401 expected without auth
                response.success()
            else:
                response.failure(f"API call failed: {response.text}")


if __name__ == "__main__":
    # Run with: locust -f load_test.py --host=http://localhost:8000
    pass
