import { lazy } from 'react';
import { Navigate } from 'react-router-dom';
import MainLayout from 'layout/MainLayout';
import Loadable from 'ui-component/Loadable';
import DashboardGrid   from 'components/dashboard-grid/DashboardGrid';
import analyticsLayout from 'views/dashboard/analytics-wireframe.json';
import Sonic from 'views/sonic';
import ErrorBoundary from './ErrorBoundary';




// project imports
const OverviewPage = Loadable(lazy(() => import('views/overview')));
const PositionsPage = Loadable(lazy(() => import('views/positions')));
const WalletManagerPage = Loadable(lazy(() => import('views/wallet/WalletManager')));
const MonitorManagerPage = Loadable(lazy(() => import('views/monitorManager/MonitorManager')));
const AlertThresholdsPage = Loadable(lazy(() => import('views/alertThresholds')));
const SonicLabsPage = Loadable(lazy(() => import('views/sonicLabs')));
const TraderFactoryPage = Loadable(
  lazy(() => import('views/traderFactory/TraderFactoryPage'))
);
const DashboardAnalytics = Loadable(lazy(() => import('views/dashboard/Analytics')));
const DashboardDefault = Loadable(lazy(() => import('views/dashboard/Default')));
const DatabaseViewer = Loadable(lazy(() => import('views/debug/DatabaseViewer')));
const XComSettingsPage = Loadable(lazy(() => import('views/xcomSettings/XComSettings')));
const HedgeReportPage = Loadable(lazy(() => import('views/hedgeReport')));
const KanbanPage = Loadable(lazy(() => import('views/kanban')));
const KanbanBoard = Loadable(lazy(() => import('views/kanban/Board')));
const KanbanBacklogs = Loadable(lazy(() => import('views/kanban/Backlogs')));

// ==============================|| MAIN ROUTING ||============================== //

const MainRoutes = {
  path: '/',
  element: <MainLayout />,
  errorElement: <ErrorBoundary />,
  children: [
    {
      index: true,
      element: <Navigate to="/sonic" />
    },
    {
      path: 'debug/db',
      element: <DatabaseViewer />
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
      path: '/monitor-manager',
      element: <MonitorManagerPage />
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
      path: '/dashboards/analytics-wire',
      element: <DashboardGrid layout={analyticsLayout} wireframe />
    },
    {

      path: '/sonic-labs',
      element: <SonicLabsPage />
    },
    {
      path: '/trader-factory',
      element: <TraderFactoryPage />
    },
    {
      path: '/communications/xcom',
      element: <XComSettingsPage />
    },
    {
      path: '/hedge-report',
      element: <HedgeReportPage />
    },
    {
      path: '/apps/kanban',
      element: <KanbanPage />,
      children: [
        { index: true, element: <Navigate to="board" /> },
        { path: 'board', element: <KanbanBoard /> },
        { path: 'backlogs', element: <KanbanBacklogs /> }
      ]
    },

    {
      path: '/sonic',
      element: <Sonic />
    }
  ]
};

export default MainRoutes;
