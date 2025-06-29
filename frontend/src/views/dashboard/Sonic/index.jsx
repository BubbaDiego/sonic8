// material-ui
import Grid from '@mui/material/Grid';

// project imports
import ValueToCollateralChartCard from './ValueToCollateralChartCard';
import PortfolioTableCard from './PortfolioTableCard';
import TotalValueCard from 'ui-component/cards/TotalValueCard';
import TotalLeverageDarkCard from 'ui-component/cards/TotalLeverageDarkCard';

import TotalLeverageLightCard from 'ui-component/cards/TotalLeverageLightCard';
import TotalSizeDarkCard from 'ui-component/cards/TotalSizeDarkCard';
import TotalSizeLightCard from 'ui-component/cards/TotalSizeLightCard';
import useConfig from 'hooks/useConfig';
import { ThemeMode } from 'config';

import UserCountCard from 'ui-component/cards/UserCountCard';

import { gridSpacing } from 'store/constant';

// assets
import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import AccountCircleTwoTone from '@mui/icons-material/AccountCircleTwoTone';
import DescriptionTwoToneIcon from '@mui/icons-material/DescriptionTwoTone';

// ==============================|| SONIC DASHBOARD ||============================== //

export default function Sonic() {
  const { mode } = useConfig();

  const LeverageCard = mode === ThemeMode.DARK ? TotalLeverageDarkCard : TotalLeverageLightCard;
  const SizeCard = mode === ThemeMode.DARK ? TotalSizeDarkCard : TotalSizeLightCard;

  return (
    <Grid container spacing={gridSpacing}>
      <Grid size={{ xs: 12, lg: 8, md: 6 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <ValueToCollateralChartCard />
          </Grid>
          <Grid size={12}>
            <PortfolioTableCard />
          </Grid>
        </Grid>
      </Grid>
      <Grid size={{ xs: 12, lg: 4, md: 6 }}>
        <Grid container spacing={gridSpacing}>
          <Grid size={12}>
            <TotalValueCard
              primary="Total Value"
              secondary="$0"
              content="1000 Shares"
              iconPrimary={MonetizationOnTwoToneIcon}
              color="secondary.main"
            />
          </Grid>
          <Grid size={12}>

            <LeverageCard isLoading={false} />
          </Grid>
          {/* display the portfolio size just below the leverage card */}
          <Grid size={12}>
            <SizeCard isLoading={false} />

            <TotalLeverageDarkCard isLoading={false} />

          </Grid>
          <Grid size={12}>
            <UserCountCard primary="Daily user" secondary="1,658" iconPrimary={AccountCircleTwoTone} color="secondary.main" />
          </Grid>
          <Grid size={12}>
            <UserCountCard primary="Daily page view" secondary="1K" iconPrimary={DescriptionTwoToneIcon} color="primary.main" />
          </Grid>
        </Grid>
      </Grid>
    </Grid>
  );
}