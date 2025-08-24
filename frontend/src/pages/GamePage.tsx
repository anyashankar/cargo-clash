import React from 'react';
import { Container, Typography, Card, CardContent, Box, Button } from '@mui/material';
import { Construction } from '@mui/icons-material';

// Placeholder pages for the remaining routes
const GamePage: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 4 }}>
    <Card>
      <CardContent sx={{ textAlign: 'center', py: 8 }}>
        <Construction sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
        <Typography variant="h4" gutterBottom>Game View</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Interactive game world with real-time vehicle tracking, combat, and world events.
        </Typography>
        <Button variant="contained" disabled>Coming Soon</Button>
      </CardContent>
    </Card>
  </Container>
);

export default GamePage;
