import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';

import { useAuth } from './contexts/AuthContext';
import { useWebSocket } from './contexts/WebSocketContext';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import GamePage from './pages/GamePage';
import VehiclesPage from './pages/VehiclesPage';
import MissionsPage from './pages/MissionsPage';
import MarketPage from './pages/MarketPage';
import AlliancesPage from './pages/AlliancesPage';
import LeaderboardPage from './pages/LeaderboardPage';
import ProfilePage from './pages/ProfilePage';

// Components
import Navbar from './components/Navbar';
import LoadingScreen from './components/LoadingScreen';
import ConnectionStatus from './components/ConnectionStatus';

function App() {
  const { user, loading } = useAuth();
  const { connectionStatus } = useWebSocket();

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <Box className="game-background" sx={{ minHeight: '100vh' }}>
      {user && <Navbar />}
      {user && <ConnectionStatus status={connectionStatus} />}
      
      <Routes>
        {/* Public routes */}
        <Route 
          path="/login" 
          element={!user ? <LoginPage /> : <Navigate to="/dashboard" />} 
        />
        <Route 
          path="/register" 
          element={!user ? <RegisterPage /> : <Navigate to="/dashboard" />} 
        />
        
        {/* Protected routes */}
        <Route 
          path="/dashboard" 
          element={user ? <DashboardPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/game" 
          element={user ? <GamePage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/vehicles" 
          element={user ? <VehiclesPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/missions" 
          element={user ? <MissionsPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/market" 
          element={user ? <MarketPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/alliances" 
          element={user ? <AlliancesPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/leaderboard" 
          element={user ? <LeaderboardPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="/profile" 
          element={user ? <ProfilePage /> : <Navigate to="/login" />} 
        />
        
        {/* Default redirect */}
        <Route 
          path="/" 
          element={<Navigate to={user ? "/dashboard" : "/login"} />} 
        />
        
        {/* Catch all */}
        <Route 
          path="*" 
          element={<Navigate to={user ? "/dashboard" : "/login"} />} 
        />
      </Routes>
    </Box>
  );
}

export default App;
