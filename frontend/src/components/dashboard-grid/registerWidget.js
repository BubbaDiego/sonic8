import MarketShareAreaChartCard from 'views/dashboard/PerformanceGraphCard';
import LatestCustomerTableCard  from 'views/dashboard/PositionListCard';
import RevenueCard              from 'ui-component/cards/RevenueCard';
import TotalRevenueCard         from 'views/dashboard/TraderListCard';

export const widgetRegistry = {
  marketShare : MarketShareAreaChartCard,
  customers   : LatestCustomerTableCard,
  revenue     : RevenueCard,
  totalRev    : TotalRevenueCard
};
