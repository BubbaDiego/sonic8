import { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
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

  const toggle = () => setMode((m) => (m === 'portfolio' ? 'operations' : 'portfolio'));

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
        <Button size="small" variant="outlined" onClick={toggle}>
          {mode === 'portfolio' ? 'Show Operations' : 'Show Portfolio'}
        </Button>
      </Box>
      {mode === 'portfolio' ? (
        <PortfolioBar data={{
          value: portfolio?.total_value,
          heatIndex: portfolio?.avg_heat_index,
          leverage: portfolio?.avg_leverage,
          size: portfolio?.total_size
        }} variant={variant} />
      ) : (
        <OperationsBar monitors={monitorStatus?.monitors || {}} variant={variant} />
      )}
    </Box>
  );
}
