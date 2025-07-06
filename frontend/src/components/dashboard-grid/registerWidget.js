import MarketShareAreaChartCard from 'views/dashboard/Analytics/MarketShareAreaChartCard';
import LatestCustomerTableCard  from 'views/dashboard/Analytics/LatestCustomerTableCard';
import RevenueCard              from 'ui-component/cards/RevenueCard';
import TotalRevenueCard         from 'views/dashboard/Analytics/TotalRevenueCard';

export const widgetRegistry = {
  marketShare : MarketShareAreaChartCard,
  customers   : LatestCustomerTableCard,
  revenue     : RevenueCard,
  totalRev    : TotalRevenueCard
};
