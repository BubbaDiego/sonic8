import {
  IconCurrencyDollar,
  IconTrendingUp,
  IconFlame,
  IconSkull,
  IconSum,
  IconArrowsMaximize,
  IconPercentage,
  IconTemperature,
  IconRoute
} from '@tabler/icons-react';

// Simple emoji components for metrics without tabler icons
const LiquidationDistanceIcon = () => <>📉</>;
const ProfitEmojiIcon = () => <>💰</>;

// Map alert types to tabler icon components
export const typeIcons = {
  PriceThreshold: IconCurrencyDollar,
  Profit: IconTrendingUp,
  TravelPercentLiquid: IconRoute,
  TravelPercent: IconRoute,
  HeatIndex: IconFlame,
  DeathNail: IconSkull,
  TotalValue: IconSum,
  TotalSize: IconArrowsMaximize,
  AvgLeverage: IconPercentage,
  AvgTravelPercent: IconRoute,
  ValueToCollateralRatio: IconPercentage,
  TotalHeat: IconTemperature,
  liquidationdistance: LiquidationDistanceIcon,
  profit: ProfitEmojiIcon
};

export default typeIcons;
