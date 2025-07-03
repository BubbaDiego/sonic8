import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { useTheme } from '@mui/material/styles';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';

import MainCard from '../MainCard';
import axios from 'utils/axios';

export default function ValueToCollateralChartCard({ isLoading }) {
  const theme = useTheme();
  const [ratio, setRatio] = useState(0);

  useEffect(() => {
    async function loadData() {
      try {
        const response = await axios.get('/portfolio/latest');
        const val = parseFloat(response.data?.value_to_collateral_ratio || 0);
        setRatio(val);
      } catch (e) {
        console.error(e);
      }
    }
    loadData();
  }, []);

  const chartData = {
    series: [ratio * 100],
    options: {
      chart: { type: 'radialBar', sparkline: { enabled: true } },
      labels: [''],
      colors: [theme.palette.primary.main],
      plotOptions: {
        radialBar: {
          dataLabels: {
            name: { show: false },
            value: {
              formatter: (val) => `${ratio.toFixed(2)}x`,
              color: theme.palette.primary.main,
              fontSize: '20px',
              show: true
            }
          }
        }
      }
    }
  };

  return (
    <MainCard title="Value/Collateral" content={false}>
      <Box sx={{ p: 2, textAlign: 'center' }}>
        {isLoading ? (
          <Typography variant="body2">Loading...</Typography>
        ) : (
          <Chart {...chartData} />
        )}
      </Box>
    </MainCard>
  );
}

ValueToCollateralChartCard.propTypes = { isLoading: PropTypes.bool };
