import Grid from '@mui/material/Grid';
import { useTheme } from '@mui/material/styles';
import TotalValueDarkCard from './TotalValueDarkCard';
import TotalValueLightCard from './TotalValueLightCard';
import TotalHeatIndexDarkCard from './TotalHeatIndexDarkCard';
import TotalHeatIndexLightCard from './TotalHeatIndexLightCard';
import TotalLeverageDarkCard from './TotalLeverageDarkCard';
import TotalLeverageLightCard from './TotalLeverageLightCard';
import TotalSizeDarkCard from './TotalSizeDarkCard';
import TotalSizeLightCard from './TotalSizeLightCard';

export default function SonicStatusRail({ data }) {
  const theme = useTheme();
  const isDark = theme.palette.mode === 'dark';

  return (
    <Grid
      container
      spacing={2}
      sx={{
        backgroundImage: 'url(/static/images/abstract_mural.png)',
        backgroundSize: 'cover',
        backgroundRepeat: 'no-repeat',
        backgroundPosition: 'center',
        borderRadius: 2,
        p: 2,
      }}
    >
      <Grid item xs={3}>
        {isDark ? <TotalValueDarkCard value={data.value} /> : <TotalValueLightCard value={data.value} />}
      </Grid>
      <Grid item xs={3}>
        {isDark ? <TotalHeatIndexDarkCard value={data.heatIndex} /> : <TotalHeatIndexLightCard value={data.heatIndex} />}
      </Grid>
      <Grid item xs={3}>
        {isDark ? <TotalLeverageDarkCard value={data.leverage} /> : <TotalLeverageLightCard value={data.leverage} />}
      </Grid>
      <Grid item xs={3}>
        {isDark ? <TotalSizeDarkCard value={data.size} /> : <TotalSizeLightCard value={data.size} />}
      </Grid>
    </Grid>
  );
}
