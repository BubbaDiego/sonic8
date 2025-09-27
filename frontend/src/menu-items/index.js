import dashboardDefault from './dashboard-default';
import positions from './positions';
import walletManager from './wallet-manager';
import monitorManager from './monitor-manager';
import sonicLabs from './sonic-labs';
import traderFactory from './traderFactory';
import kanban from './kanban';
import sonic from './sonic';
import themeLab from './theme-lab';
import jupiter from './jupiter';
import xcom from './xcom';

const menuItems = {
  items: [
    {
      id: 'main-pages',
      // omit title so sidebar has no heading
      type: 'group',
      children: [
        sonic,
        monitorManager,
        xcom,
        positions,
        walletManager,
        kanban,
        sonicLabs,
        themeLab,
        jupiter,
        traderFactory,
        dashboardDefault
      ]
    }
  ]
};

export default menuItems;
