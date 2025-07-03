import PropTypes from 'prop-types';
import useMediaQuery from '@mui/material/useMediaQuery';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

// third party
import Chart from 'react-apexcharts';

// project imports
import MainCard from './MainCard';

export default function SeoChartCard({ chartData, value, title, icon, type }) {
  const downMM = useMediaQuery((theme) => theme.breakpoints.down('md'));

  return (
    <MainCard content={false} sx={{ p: 2.5 }}>
      <Grid container spacing={1.25} sx={{ justifyContent: 'space-between' }}>
        <Grid size={12}>
          <Stack direction={type === 1 ? 'column-reverse' : 'column'} spacing={type === 1 ? 0.5 : 1}>
            {value && <Typography variant={downMM ? 'h4' : 'h3'}>{value}</Typography>}
            {(title || icon) && (
              <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                {title && (
                  <Typography variant="body1" sx={{ color: 'grey.500' }}>
                    {title}
                  </Typography>
                )}
                {icon && icon}
              </Stack>
            )}
          </Stack>
        </Grid>
        {chartData && (
          <Grid size={12}>
            <Chart {...chartData} />
          </Grid>
        )}
      </Grid>
    </MainCard>
  );
}

SeoChartCard.propTypes = {
  chartData: PropTypes.any,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  title: PropTypes.string,
  icon: PropTypes.oneOfType([PropTypes.node, PropTypes.string]),
  type: PropTypes.number
};
