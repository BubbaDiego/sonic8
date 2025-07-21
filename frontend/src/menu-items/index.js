import dashboardDefault from './dashboard-default';
import positions from './positions';
import alertThresholds from './alert-thresholds';
import walletManager from './wallet-manager';
import sonicLabs from './sonic-labs';
import traderShop from './traderShop';
import traderFactory from './traderFactory';
import kanban from './kanban';
import sonic from './sonic';

const menuItems = {
  items: [
    {
      id: 'main-pages',
      title: 'Main Pages',
      type: 'group',
      children: [
        sonic,
        dashboardDefault,
        positions,
        walletManager,
        alertThresholds,
        kanban,
        sonicLabs,
        traderShop,
        traderFactory
      ]
    }
  ]
};

export default menuItems;
