import overview from './overview';
import analytics from './analytics';
import dashboardDefault from './dashboard-default';
import positions from './positions';
import alertThresholds from './alert-thresholds';
import walletManager from './wallet-manager';
import sonicLabs from './sonic-labs';
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
        sonicLabs
      ]
    },
    pages
  ]
};

export default menuItems;
