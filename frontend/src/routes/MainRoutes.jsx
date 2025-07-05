import { lazy } from 'react';
import { Navigate } from 'react-router-dom';
import MainLayout from 'layout/MainLayout';
import Loadable from 'ui-component/Loadable';

// existing imports
const OverviewPage = Loadable(lazy(() => import('views/overview')));
const PositionsPage = Loadable(lazy(() => import('views/positions')));
const ThresholdsPage = Loadable(lazy(() => import('views/alert-thresholds')));
const WalletManagerPage = Loadable(lazy(() => import('views/wallet/WalletManager')));
const AlertThresholdsPage = Loadable(lazy(() => import('views/alertThresholds')));

// ==============================|| MAIN ROUTING ||============================== //

const MainRoutes = {
  path: '/',
  element: <MainLayout />,
  children: [
    {
      index: true,
      element: <Navigate to="/overview" />
    },
    {
      path: '/overview',
      element: <OverviewPage />
    },
    {
      path: '/positions',
      element: <PositionsPage />
    },
    {
      path: '/alert-thresholds',
      element: <ThresholdsPage />
    },
    {
      path: '/wallet-manager',
      element: <WalletManagerPage />
    },
    {
      path: '/alert-thresholds',
      element: <AlertThresholdsPage />
    }
  ]
};

export default MainRoutes;
