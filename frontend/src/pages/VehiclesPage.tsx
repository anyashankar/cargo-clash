import React from 'react';
import { Container, Typography, Card, CardContent, Box, Button } from '@mui/material';
import { DirectionsCar } from '@mui/icons-material';

const VehiclesPage: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 4 }}>
    <Typography variant="h4" gutterBottom>My Vehicles</Typography>
    <Card>
      <CardContent sx={{ textAlign: 'center', py: 8 }}>
        <DirectionsCar sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>Vehicle Management</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Manage your fleet, upgrade vehicles, track travel progress, and handle maintenance.
        </Typography>
        <Button variant="contained" disabled>Coming Soon</Button>
      </CardContent>
    </Card>
  </Container>
);

export default VehiclesPage;
