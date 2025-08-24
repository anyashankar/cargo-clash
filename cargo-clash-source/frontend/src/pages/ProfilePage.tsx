import React from 'react';
import { Container, Typography, Card, CardContent, Button } from '@mui/material';
import { AccountCircle } from '@mui/icons-material';

const ProfilePage: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 4 }}>
    <Typography variant="h4" gutterBottom>Profile</Typography>
    <Card>
      <CardContent sx={{ textAlign: 'center', py: 8 }}>
        <AccountCircle sx={{ fontSize: 80, color: 'primary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>Player Profile</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Manage your profile, view statistics, achievements, and game history.
        </Typography>
        <Button variant="contained" disabled>Coming Soon</Button>
      </CardContent>
    </Card>
  </Container>
);

export default ProfilePage;
