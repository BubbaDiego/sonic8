import { lazy } from 'react';
import { Navigate } from 'react-router-dom';
import MainLayout from 'layout/MainLayout';
import Loadable from 'ui-component/Loadable';

// project imports
const OverviewPage = Loadable(lazy(() => import('views/overview')));
const PositionsPage = Loadable(lazy(() => import('views/positions')));
const WalletManagerPage = Loadable(lazy(() => import('views/wallet/WalletManager')));
const AlertThresholdsPage = Loadable(lazy(() => import('views/alertThresholds')));
const SonicLabsPage = Loadable(lazy(() => import('views/sonicLabs')));
const DashboardAnalytics = Loadable(lazy(() => import('views/dashboard/Analytics')));
const DashboardDefault = Loadable(lazy(() => import('views/dashboard/Default')));

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
      path: '/wallet-manager',
      element: <WalletManagerPage />
    },
    {
      path: '/alert-thresholds',
      element: <AlertThresholdsPage />
    },
    {
      path: '/dashboard/analytics',
      element: <DashboardAnalytics />
    },
    {
      path: '/dashboard/default',
      element: <DashboardDefault />
    },
    {
      path: '/sonic-labs',
      element: <SonicLabsPage />
    }
  ]
};

export default MainRoutes;
