import { Grid } from '@mui/material';
import PositionsTableCard from 'ui-component/cards/positions/PositionsTableCard';
import LiquidationBarsCard from 'views/positions/LiquidationBarsCard';

const PositionsPage = () => (
  <Grid container spacing={2}>
    <Grid item xs={12}>
      <PositionsTableCard />
    </Grid>
    <Grid item xs={12}>
      <LiquidationBarsCard />
    </Grid>
  </Grid>
);

export default PositionsPage;

