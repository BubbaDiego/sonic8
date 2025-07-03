import PropTypes from 'prop-types';

// material-ui
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// third party
import Chart from 'react-apexcharts';

// ============================|| SALES LINE CARD ||============================ //

export default function SalesLineChartCard({ bgColor, chartData, footerData, icon, title, percentage }) {
  let footerHtml;
  if (footerData) {
    footerHtml = footerData.map((item, index) => (
      <Grid key={index}>
        <Box sx={{ my: 3, p: 1 }}>
          <Stack spacing={0.75} sx={{ alignItems: 'center' }}>
            <Typography variant="h3">{item.value}</Typography>
            <Typography variant="body1">{item.label}</Typography>
          </Stack>
        </Box>
      </Grid>
    ));
  }

  return (
    <Card>
      <Box sx={{ color: '#fff', bgcolor: bgColor || 'primary.dark', p: 3 }}>
        <Grid container direction="column" spacing={1}>
          <Grid container sx={{ justifyContent: 'space-between', alignItems: 'center' }}>
            {title && (
              <Grid>
                <Typography variant="subtitle1" color="inherit">
                  {title}
                </Typography>
              </Grid>
            )}
            <Grid>
              <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
                {icon && icon}
                {percentage && (
                  <Typography variant="subtitle1" color="inherit">
                    {percentage}
                  </Typography>
                )}
              </Stack>
            </Grid>
          </Grid>
          {chartData && (
            <Grid>
              <Chart {...chartData} />
            </Grid>
          )}
        </Grid>
      </Box>
      {footerData && (
        <Grid container sx={{ alignItems: 'center', justifyContent: 'space-around' }}>
          {footerHtml}
        </Grid>
      )}
    </Card>
  );
}

SalesLineChartCard.propTypes = {
  bgColor: PropTypes.string,
  chartData: PropTypes.any,
  footerData: PropTypes.object,
  icon: PropTypes.oneOfType([PropTypes.node, PropTypes.string]),
  title: PropTypes.string,
  percentage: PropTypes.string
};
