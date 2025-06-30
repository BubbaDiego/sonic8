// material-ui
import Grid from '@mui/material/Grid';

// project imports
import ValueToCollateralChartCard from './ValueToCollateralChartCard';
import PortfolioTableCard from './PortfolioTableCard';
import TotalValueCard from 'ui-component/cards/TotalValueCard';
import TotalLeverageDarkCard from 'ui-component/cards/TotalLeverageDarkCard';
import TotalLeverageLightCard from 'ui-component/cards/TotalLeverageLightCard';
import TotalHeatIndexDarkCard from 'ui-component/cards/TotalHeatIndexDarkCard';
import TotalHeatIndexLightCard from 'ui-component/cards/TotalHeatIndexLightCard';
import TotalSizeDarkCard from 'ui-component/cards/TotalSizeDarkCard';
import TotalSizeLightCard from 'ui-component/cards/TotalSizeLightCard';
import useConfig from 'hooks/useConfig';
import { ThemeMode } from 'config';
import UserCountCard from 'ui-component/cards/UserCountCard';
import SizeHedgeChartCard from './SizeHedgeChartCard';

import { gridSpacing } from 'store/constant';

// assets
import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import AccountCircleTwoTone from '@mui/icons-material/AccountCircleTwoTone';
import DescriptionTwoToneIcon from '@mui/icons-material/DescriptionTwoTone';

// ==============================|| SONIC DASHBOARD ||============================== //

export default function Sonic() {
  const { mode } = useConfig();

  const LeverageCard = mode === ThemeMode.DARK ? TotalLeverageDarkCard : TotalLeverageLightCard;
  const HeatIndexCard = mode === ThemeMode.DARK ? TotalHeatIndexDarkCard : TotalHeatIndexLightCard;
  const SizeCard = mode === ThemeMode.DARK ? TotalSizeDarkCard : TotalSizeLightCard;

  return (
    <Grid container spacing={gridSpacing}>
      <Grid item xs={12}>
        <Grid container spacing={gridSpacing}>
          <Grid item xs={12} lg={8} md={8}>
            <PortfolioTableCard />
          </Grid>
          <Grid item xs={12} lg={4} md={4}>
            <ValueToCollateralChartCard />
          </Grid>
        </Grid>
      </Grid>

      <Grid item xs={12}>
        <Grid container spacing={gridSpacing}>
          <Grid item xs={12} md={4}>
            <TotalValueCard
              primary="Total Value"
              secondary="$0"
              content="1000 Shares"
              iconPrimary={MonetizationOnTwoToneIcon}
              color="secondary.main"
            />
          </Grid>
          <Grid item xs={12} md={4}>
            <LeverageCard isLoading={false} />
          </Grid>
          <Grid item xs={12} md={4}>
            <HeatIndexCard isLoading={false} />
          </Grid>
        </Grid>
      </Grid>

      <Grid item xs={12}>
        <Grid container spacing={gridSpacing}>
          <Grid item xs={12} md={4}>
            <SizeCard isLoading={false} />
          </Grid>
          <Grid item xs={12} md={8}>
            <SizeHedgeChartCard />
          </Grid>
        </Grid>
      </Grid>

      <Grid item xs={12}>
        <Grid container spacing={gridSpacing}>
          <Grid item xs={12} md={4}>
            <UserCountCard primary="Daily user" secondary="1,658" iconPrimary={AccountCircleTwoTone} color="secondary.main" />
          </Grid>
          <Grid item xs={12} md={4}>
            <UserCountCard primary="Daily page view" secondary="1K" iconPrimary={DescriptionTwoToneIcon} color="primary.main" />
          </Grid>
        </Grid>
      </Grid>
    </Grid>
  );
}
