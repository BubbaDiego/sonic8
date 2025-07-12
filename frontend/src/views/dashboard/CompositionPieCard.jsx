import { useEffect, useState } from 'react';
import { useTheme } from '@mui/material/styles';
import Box from '@mui/material/Box';
import Chart from 'react-apexcharts';
import MainCard from 'ui-component/cards/MainCard';
import { useGetLatestPortfolio } from 'api/portfolio';
import PropTypes from 'prop-types';

export default function CompositionPieCard({ maxHeight = 115, maxWidth = 190 }) {
  const theme = useTheme();
  const { portfolio, portfolioLoading } = useGetLatestPortfolio();

  const [series, setSeries] = useState([0, 0]);

  const totalValue = series.reduce((acc, val) => acc + val, 0);
  const percentages = series.map(val => totalValue > 0 ? Math.round((val / totalValue) * 100) : 0);

  const chartOptions = {
    labels: [`Long (${percentages[0]}%)`, `Short (${percentages[1]}%)`],
    colors: [theme.palette.success.main, theme.palette.error.main],
    legend: { show: false },
    tooltip: { theme: theme.palette.mode === 'dark' ? 'dark' : 'light' },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${Math.round(val)}%`,
      style: {
        fontSize: '12px',
        colors: ['#ffffff'], // white text for labels
      },
      dropShadow: {
        enabled: false,
      }
    },
    plotOptions: {
      pie: {
        dataLabels: {
          offset: -20, // move closer to center (negative offset)
        }
      }
    },
  };

  useEffect(() => {
    if (portfolioLoading || !portfolio) return;

    const longSize = portfolio.total_long_size || 0;
    const shortSize = portfolio.total_short_size || 0;

    setSeries([longSize, shortSize]);
  }, [portfolio, portfolioLoading]);

  return (
    <MainCard
      sx={{
        height: '100%',
        maxHeight,
        maxWidth,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 2
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Chart
          options={chartOptions}
          series={series}
          type="pie"
          height={120}
          width={120}
        />
      </Box>
    </MainCard>
  );
}

CompositionPieCard.propTypes = {
  maxHeight: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  maxWidth: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
};
