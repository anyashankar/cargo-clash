import React from 'react';
import { Chip, Box } from '@mui/material';
import { Wifi, WifiOff, Warning } from '@mui/icons-material';

interface ConnectionStatusProps {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ status }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'connected':
        return {
          label: 'Connected',
          color: 'success' as const,
          icon: <Wifi />,
        };
      case 'connecting':
        return {
          label: 'Connecting...',
          color: 'warning' as const,
          icon: <Warning />,
        };
      case 'error':
        return {
          label: 'Connection Error',
          color: 'error' as const,
          icon: <WifiOff />,
        };
      case 'disconnected':
      default:
        return {
          label: 'Disconnected',
          color: 'error' as const,
          icon: <WifiOff />,
        };
    }
  };

  const config = getStatusConfig();

  // Only show if not connected
  if (status === 'connected') {
    return null;
  }

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 80,
        right: 16,
        zIndex: 1300,
      }}
    >
      <Chip
        icon={config.icon}
        label={config.label}
        color={config.color}
        variant="filled"
        size="small"
        sx={{
          animation: status === 'connecting' ? 'pulse 2s infinite' : 'none',
          '@keyframes pulse': {
            '0%': {
              opacity: 1,
            },
            '50%': {
              opacity: 0.5,
            },
            '100%': {
              opacity: 1,
            },
          },
        }}
      />
    </Box>
  );
};

export default ConnectionStatus;
