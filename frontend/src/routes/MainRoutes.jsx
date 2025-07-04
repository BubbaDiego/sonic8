import { lazy } from 'react';
import MainLayout from 'layout/MainLayout';
import Loadable from 'ui-component/Loadable';

// existing imports
const SamplePage = Loadable(lazy(() => import('views/sample-page')));
const PositionsPage = Loadable(lazy(() => import('views/positions')));

// new import
const WalletManagerPage = Loadable(lazy(() => import('views/wallet-manager')));

// ==============================|| MAIN ROUTING ||============================== //

const MainRoutes = {
  path: '/',
  element: <MainLayout />,
  children: [
    {
      path: '/sample-page',
      element: <SamplePage />
    },
    {
      path: '/positions',
      element: <PositionsPage />
    },
    {
      path: '/wallet-manager',
      element: <WalletManagerPage />
    }
  ]
};

export default MainRoutes;
