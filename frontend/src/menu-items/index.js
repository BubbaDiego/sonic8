import samplePage from './sample-page';
import positions from './positions';
import walletManager from './wallet-manager';
import pages from './pages';

const menuItems = {
  items: [
    {
      id: 'main-pages',
      title: 'Main Pages',
      type: 'group',
      children: [
        samplePage,
        positions,
        walletManager
      ]
    },
    pages
  ]
};

export default menuItems;
