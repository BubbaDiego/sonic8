import { useState, useEffect } from 'react';
import Box from '@mui/material/Box';
import PortfolioBar from './PortfolioBar';
import OperationsBar from './OperationsBar';
import { useGetLatestPortfolio, refreshLatestPortfolio } from 'api/portfolio';
import { useGetMonitorStatus, refreshMonitorStatus } from 'api/monitorStatus';
import { useTheme } from '@mui/material/styles';

export default function DashboardToggle() {
  const theme = useTheme();
  const variant = theme.palette.mode === 'dark' ? 'dark' : 'light';
  const [mode, setMode] = useState('portfolio');
  const { portfolio } = useGetLatestPortfolio();
  const { monitorStatus } = useGetMonitorStatus();

  useEffect(() => {
    const id = setInterval(() => {
      refreshLatestPortfolio();
      refreshMonitorStatus();
    }, 60000);
    return () => clearInterval(id);
  }, []);

  const toggle = () => setMode(m => (m === 'portfolio' ? 'operations' : 'portfolio'));

  return (
    <Box sx={{ perspective: 1000 }}>
      <Box
        sx={{
          position: 'relative',
          width: '100%',
          transition: 'transform 0.6s',
          transformStyle: 'preserve-3d',
          transform: mode === 'portfolio' ? 'rotateY(0deg)' : 'rotateY(180deg)'
        }}
      >
        {/* Front face */}
        <Box sx={{ backfaceVisibility: 'hidden' }}>
          <PortfolioBar
            data={{
              value: portfolio?.total_value,
              heatIndex: portfolio?.avg_heat_index,
              leverage: portfolio?.avg_leverage,
              size: portfolio?.total_size,
              travelPercent: portfolio?.total_travel_percent
            }}
            variant={variant}
            onToggle={toggle}
          />
        </Box>

        {/* Back face */}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            width: '100%',
            transform: 'rotateY(180deg)',
            backfaceVisibility: 'hidden'
          }}
        >
          <OperationsBar
            monitors={monitorStatus?.monitors || {}}
            variant={variant}
            onToggle={toggle}
          />
        </Box>
      </Box>
    </Box>
  );
}
