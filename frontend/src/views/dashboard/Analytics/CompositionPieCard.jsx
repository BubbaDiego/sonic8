
import { useEffect, useState } from 'react';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { useGetLatestPortfolio } from 'api/portfolio';
import PropTypes from 'prop-types';

export default function CompositionPieCard({ maxHeight, maxWidth }) {
  const theme = useTheme();
  const { portfolio, portfolioLoading } = useGetLatestPortfolio();

  const [series, setSeries] = useState([0, 0]);
  const chartOptions = {
    labels: ['Long', 'Short'],
    colors: [theme.palette.success.main, theme.palette.error.main],
    legend: { show: false },
    tooltip: { theme: theme.palette.mode === 'dark' ? 'dark' : 'light' },
    dataLabels: { enabled: false },
  };

  useEffect(() => {
    if (portfolioLoading || !portfolio) return;

    const longSize = portfolio.total_long_size || 0;
    const shortSize = portfolio.total_short_size || 0;

    setSeries([longSize, shortSize]);
  }, [portfolio, portfolioLoading]);

  maxHeight = 115
  maxWidth = 190

  return (
    <MainCard
      sx={{
        height: '100%',
        maxHeight: maxHeight || 'none', // Dynamically sets max height if provided
        maxWidth: maxWidth || 'none',   // Dynamically sets max width if provided
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Chart options={chartOptions} series={series} type="pie" height={120} width={120} />
      </Box>
    </MainCard>
  );
}

// Prop validation
CompositionPieCard.propTypes = {
  maxHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  maxWidth: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
};
