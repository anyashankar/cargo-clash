import React from 'react';
import { Container, Typography, Card, CardContent, Button } from '@mui/material';
import { Store } from '@mui/icons-material';

const MarketPage: React.FC = () => (
  <Container maxWidth="xl" sx={{ py: 4 }}>
    <Typography variant="h4" gutterBottom>Market</Typography>
    <Card>
      <CardContent sx={{ textAlign: 'center', py: 8 }}>
        <Store sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>Trading Hub</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Buy and sell cargo, monitor price trends, and find arbitrage opportunities.
        </Typography>
        <Button variant="contained" disabled>Coming Soon</Button>
      </CardContent>
    </Card>
  </Container>
);

export default MarketPage;
