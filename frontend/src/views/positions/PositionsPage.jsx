import { Grid } from '@mui/material';
import PositionsTableCard from 'ui-component/cards/positions/PositionsTableCard';

const PositionsPage = () => (
  <Grid container spacing={2}>
    <Grid item xs={12}>
      <PositionsTableCard />
    </Grid>
  </Grid>
);

export default PositionsPage;

