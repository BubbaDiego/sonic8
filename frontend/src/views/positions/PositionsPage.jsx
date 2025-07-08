import { Grid } from '@mui/material';
import PositionTableCard from './PositionTableCard';
import LiquidationBarsCard from './LiquidationBarsCard';

const PositionsPage = () => (
  <Grid container spacing={2}>
    <Grid item xs={12}>
      <PositionTableCard />
    </Grid>
    <Grid item xs={12}>
      <div style={{ width: '100%', border: '2px solid yellow' }}>
        <LiquidationBarsCard />
      </div>
    </Grid>
  </Grid>
);

export default PositionsPage;
