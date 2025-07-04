import { Typography, Grid } from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';

const WalletManagerPage = () => (
  <MainCard title="Wallet Manager">
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Typography variant="h4">Wallet Manager Coming Soon!</Typography>
        <Typography variant="body1">
          This page is under construction. Check back soon for updates!
        </Typography>
      </Grid>
    </Grid>
  </MainCard>
);

export default WalletManagerPage;
