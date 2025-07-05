import overview from './overview';
import positions from './positions';
import walletManager from './wallet-manager';
import alertThresholds from './alert-thresholds';
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
        walletManager,
        alertThresholds
      ]
    },
    pages
  ]
};

export default menuItems;
