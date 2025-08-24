import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  Box,
  Chip,
  Badge,
} from '@mui/material';
import {
  AccountCircle,
  DirectionsCar,
  Assignment,
  Store,
  Group,
  Leaderboard,
  Dashboard,
  ExitToApp,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useGame } from '../contexts/GameContext';

const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { gameState } = useGame();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    await logout();
    handleClose();
  };

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: <Dashboard /> },
    { label: 'Game', path: '/game', icon: <DirectionsCar /> },
    { label: 'Vehicles', path: '/vehicles', icon: <DirectionsCar /> },
    { label: 'Missions', path: '/missions', icon: <Assignment /> },
    { label: 'Market', path: '/market', icon: <Store /> },
    { label: 'Alliances', path: '/alliances', icon: <Group /> },
    { label: 'Leaderboard', path: '/leaderboard', icon: <Leaderboard /> },
  ];

  return (
    <AppBar position="static" sx={{ background: 'rgba(26, 31, 46, 0.95)', backdropFilter: 'blur(10px)' }}>
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ 
            flexGrow: 0, 
            mr: 4, 
            fontWeight: 'bold',
            background: 'linear-gradient(45deg, #2196f3, #ff9800)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            cursor: 'pointer',
          }}
          onClick={() => navigate('/dashboard')}
        >
          Cargo Clash
        </Typography>

        <Box sx={{ flexGrow: 1, display: { xs: 'none', md: 'flex' } }}>
          {navItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              startIcon={item.icon}
              onClick={() => navigate(item.path)}
              sx={{ 
                mx: 1,
                '&:hover': {
                  background: 'rgba(33, 150, 243, 0.1)',
                },
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>

        {/* Online players indicator */}
        {gameState && (
          <Chip
            label={`${gameState.onlinePlayers} online`}
            color="success"
            size="small"
            sx={{ mr: 2 }}
          />
        )}

        {/* User info and menu */}
        {user && (
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Box sx={{ mr: 2, textAlign: 'right' }}>
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                {user.username}
              </Typography>
              <Typography variant="caption" sx={{ opacity: 0.7 }}>
                Level {user.level} • {user.credits.toLocaleString()} credits
              </Typography>
            </Box>
            
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              onClick={handleMenu}
              color="inherit"
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                {user.username.charAt(0).toUpperCase()}
              </Avatar>
            </IconButton>
            
            <Menu
              id="menu-appbar"
              anchorEl={anchorEl}
              anchorOrigin={{
                vertical: 'bottom',
                horizontal: 'right',
              }}
              keepMounted
              transformOrigin={{
                vertical: 'top',
                horizontal: 'right',
              }}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              <MenuItem onClick={() => { navigate('/profile'); handleClose(); }}>
                <AccountCircle sx={{ mr: 1 }} />
                Profile
              </MenuItem>
              <MenuItem onClick={handleLogout}>
                <ExitToApp sx={{ mr: 1 }} />
                Logout
              </MenuItem>
            </Menu>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
