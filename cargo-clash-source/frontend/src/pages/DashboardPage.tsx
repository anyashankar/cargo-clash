import React, { useEffect, useState } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  LinearProgress,
  Chip,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider,
} from '@mui/material';
import {
  DirectionsCar,
  Assignment,
  TrendingUp,
  Group,
  Warning,
  CheckCircle,
  Schedule,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useGame } from '../contexts/GameContext';
import { useWebSocket } from '../contexts/WebSocketContext';

const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { vehicles, missions, gameState } = useGame();
  const { connectionStatus } = useWebSocket();
  const [recentActivity, setRecentActivity] = useState<any[]>([]);

  useEffect(() => {
    // Mock recent activity data
    setRecentActivity([
      {
        id: 1,
        type: 'mission_completed',
        title: 'Mission Completed',
        description: 'Delivered electronics to New Harbor',
        timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
        icon: <CheckCircle color="success" />,
      },
      {
        id: 2,
        type: 'vehicle_arrived',
        title: 'Vehicle Arrived',
        description: 'Cargo Hauler reached Port City',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
        icon: <DirectionsCar color="primary" />,
      },
      {
        id: 3,
        type: 'market_alert',
        title: 'Market Alert',
        description: 'Food prices surged in Eastern Region',
        timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4), // 4 hours ago
        icon: <TrendingUp color="warning" />,
      },
    ]);
  }, []);

  const experienceToNextLevel = user ? user.level * 1000 : 1000;
  const experienceProgress = user ? (user.experience / experienceToNextLevel) * 100 : 0;

  const activeMissions = missions.filter(m => 
    m.status === 'accepted' || m.status === 'in_progress'
  );
  const travelingVehicles = vehicles.filter(v => v.is_traveling);

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 60) {
      return `${diffInMinutes}m ago`;
    } else if (diffInMinutes < 1440) {
      return `${Math.floor(diffInMinutes / 60)}h ago`;
    } else {
      return `${Math.floor(diffInMinutes / 1440)}d ago`;
    }
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold', mb: 4 }}>
          Welcome back, {user?.username}!
        </Typography>

        <Grid container spacing={3}>
          {/* Player Stats */}
          <Grid item xs={12} md={8}>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
                    {user?.username.charAt(0).toUpperCase()}
                  </Avatar>
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="h6">{user?.username}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Level {user?.level} • {user?.reputation} Reputation
                    </Typography>
                  </Box>
                  <Chip
                    label={connectionStatus === 'connected' ? 'Online' : 'Offline'}
                    color={connectionStatus === 'connected' ? 'success' : 'error'}
                    size="small"
                  />
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Experience</Typography>
                    <Typography variant="body2">
                      {user?.experience} / {experienceToNextLevel}
                    </Typography>
                  </Box>
                  <LinearProgress 
                    variant="determinate" 
                    value={experienceProgress} 
                    sx={{ height: 8, borderRadius: 4 }}
                  />
                </Box>

                <Typography variant="h4" sx={{ fontWeight: 'bold', color: 'success.main' }}>
                  {user?.credits.toLocaleString()} Credits
                </Typography>
              </CardContent>
            </Card>

            {/* Quick Stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={6} sm={3}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <DirectionsCar color="primary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h6">{vehicles.length}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Vehicles
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Assignment color="secondary" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h6">{activeMissions.length}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Active Missions
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Schedule color="warning" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h6">{travelingVehicles.length}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Traveling
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6} sm={3}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Group color="info" sx={{ fontSize: 40, mb: 1 }} />
                    <Typography variant="h6">{gameState?.onlinePlayers || 0}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Online Players
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Quick Actions */}
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Actions
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Button
                      fullWidth
                      variant="contained"
                      startIcon={<DirectionsCar />}
                      onClick={() => navigate('/vehicles')}
                    >
                      Manage Vehicles
                    </Button>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Button
                      fullWidth
                      variant="contained"
                      color="secondary"
                      startIcon={<Assignment />}
                      onClick={() => navigate('/missions')}
                    >
                      Find Missions
                    </Button>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<TrendingUp />}
                      onClick={() => navigate('/market')}
                    >
                      Market
                    </Button>
                  </Grid>
                  <Grid item xs={12} sm={6} md={3}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={<Group />}
                      onClick={() => navigate('/alliances')}
                    >
                      Alliances
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Recent Activity */}
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Activity
                </Typography>
                <List>
                  {recentActivity.map((activity, index) => (
                    <React.Fragment key={activity.id}>
                      <ListItem alignItems="flex-start">
                        <ListItemAvatar>
                          {activity.icon}
                        </ListItemAvatar>
                        <ListItemText
                          primary={activity.title}
                          secondary={
                            <>
                              <Typography variant="body2" color="text.secondary">
                                {activity.description}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {formatTimeAgo(activity.timestamp)}
                              </Typography>
                            </>
                          }
                        />
                      </ListItem>
                      {index < recentActivity.length - 1 && <Divider variant="inset" component="li" />}
                    </React.Fragment>
                  ))}
                </List>
              </CardContent>
            </Card>

            {/* Active Events */}
            {gameState?.activeEvents && gameState.activeEvents.length > 0 && (
              <Card sx={{ mt: 2 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Active World Events
                  </Typography>
                  {gameState.activeEvents.map((event) => (
                    <Box key={event.id} sx={{ mb: 2, p: 2, bgcolor: 'warning.dark', borderRadius: 1 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                        {event.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {event.description}
                      </Typography>
                      <Chip
                        label={`Severity: ${event.severity}/10`}
                        size="small"
                        color="warning"
                        sx={{ mt: 1 }}
                      />
                    </Box>
                  ))}
                </Card>
              </Card>
            )}
          </Grid>
        </Grid>
      </motion.div>
    </Container>
  );
};

export default DashboardPage;
