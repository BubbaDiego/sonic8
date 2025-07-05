import overview from './overview';
import positions from './positions';
import alertThresholds from './alert-thresholds';
import walletManager from './wallet-manager';
import pages from './pages';

const menuItems = {
  items: [
    {
      id: 'main-pages',
      title: 'Main Pages',
      type: 'group',
      children: [
        overview,
        positions,
        alertThresholds,
        walletManager
      ]
    },
    pages
  ]
};

export default menuItems;
