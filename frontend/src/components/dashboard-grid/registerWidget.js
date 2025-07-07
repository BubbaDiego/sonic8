import MarketShareAreaChartCard from 'views/dashboard/Analytics/PerformanceGraphCard';
import LatestCustomerTableCard  from 'views/dashboard/Analytics/PositionListCard';
import RevenueCard              from 'ui-component/cards/RevenueCard';
import TotalRevenueCard         from 'views/dashboard/Analytics/TraderListCard';

export const widgetRegistry = {
  marketShare : MarketShareAreaChartCard,
  customers   : LatestCustomerTableCard,
  revenue     : RevenueCard,
  totalRev    : TotalRevenueCard
};
