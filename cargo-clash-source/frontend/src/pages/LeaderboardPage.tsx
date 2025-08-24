import React from 'react';
import { Container, Typography, Card, CardContent, Button } from '@mui/material';
import { Leaderboard } from '@mui/icons-material';

const LeaderboardPage: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 4 }}>
    <Typography variant="h4" gutterBottom>Leaderboard</Typography>
    <Card>
      <CardContent sx={{ textAlign: 'center', py: 8 }}>
        <Leaderboard sx={{ fontSize: 80, color: 'warning.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>Global Rankings</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          View top players by credits, reputation, missions completed, and more.
        </Typography>
        <Button variant="contained" disabled>Coming Soon</Button>
      </CardContent>
    </Card>
  </Container>
);

export default LeaderboardPage;
