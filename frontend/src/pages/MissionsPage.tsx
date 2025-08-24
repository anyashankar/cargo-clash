import React from 'react';
import { Container, Typography, Card, CardContent, Button } from '@mui/material';
import { Assignment } from '@mui/icons-material';

const MissionsPage: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 4 }}>
    <Typography variant="h4" gutterBottom>Missions</Typography>
    <Card>
      <CardContent sx={{ textAlign: 'center', py: 8 }}>
        <Assignment sx={{ fontSize: 80, color: 'secondary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>Mission Control</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Browse available missions, track progress, and complete deliveries for rewards.
        </Typography>
        <Button variant="contained" disabled>Coming Soon</Button>
      </CardContent>
    </Card>
  </Container>
);

export default MissionsPage;
