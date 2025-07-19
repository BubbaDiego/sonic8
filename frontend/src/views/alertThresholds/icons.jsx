import React from 'react';
import {
  IconTrendingUp,
  IconTrendingDown,
  IconArrowsMaximize,
  IconCoin,
  IconFlame,
  IconScale,
  IconAlertTriangle,
  IconCurrencyDollar,
  IconPercentage,
  IconChartBar,
} from '@tabler/icons-react';

// Emoji fallback icons
export const LiquidationDistanceIcon = () => <>📉</>;
export const ProfitEmojiIcon = () => <>💰</>;

// Map alert types to icon components
export const alertTypeIcons = {
  PriceThreshold: IconTrendingUp,
  Profit: ProfitEmojiIcon,
  Loss: IconTrendingDown,
  LiquidationDistance: LiquidationDistanceIcon,
  TravelPercent: IconArrowsMaximize,
  Collateral: IconCoin,
  HeatIndex: IconFlame,
  Leverage: IconScale,
  ValueToCollateralRatio: IconPercentage,
  TotalHeat: IconAlertTriangle,
  TotalSize: IconChartBar,
  TotalValue: IconCurrencyDollar,
  AvgTravelPercent: IconPercentage,
  AvgLeverage: IconScale,
};
