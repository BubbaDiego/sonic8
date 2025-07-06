// DashRowContainer.jsx
import Grid from 'components/AppGrid';
import { gridSpacing } from 'store/constant';

const DashRowContainer = ({ leftComponent, rightComponent }) => (
  <Grid container spacing={gridSpacing}>
    <Grid size={{ xs: 12, md: 6 }}>
      {leftComponent}
    </Grid>
    <Grid size={{ xs: 12, md: 6 }}>
      {rightComponent}
    </Grid>
  </Grid>
);

export default DashRowContainer;
