import overview from './overview';
import analytics from './analytics';
import dashboardDefault from './dashboard-default';
import positions from './positions';
import alertThresholds from './alert-thresholds';
import walletManager from './wallet-manager';
import sonicLabs from './sonic-labs';
import traderShop from './traderShop';
import pages from './pages';

const menuItems = {
  items: [
    {
      id: 'main-pages',
      title: 'Main Pages',
      type: 'group',
      children: [
        overview,
        analytics,
        dashboardDefault,
        positions,
        walletManager,
        alertThresholds,
        sonicLabs,
        traderShop
      ]
    },
    pages
  ]
};

export default menuItems;
