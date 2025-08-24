import React from 'react';
import { Container, Typography, Card, CardContent, Button } from '@mui/material';
import { Group } from '@mui/icons-material';

const AlliancesPage: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 4 }}>
    <Typography variant="h4" gutterBottom>Alliances</Typography>
    <Card>
      <CardContent sx={{ textAlign: 'center', py: 8 }}>
        <Group sx={{ fontSize: 80, color: 'info.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>Alliance System</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Join or create alliances, coordinate with other players, and participate in faction wars.
        </Typography>
        <Button variant="contained" disabled>Coming Soon</Button>
      </CardContent>
    </Card>
  </Container>
);

export default AlliancesPage;
