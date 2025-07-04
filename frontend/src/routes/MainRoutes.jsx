import { lazy } from 'react';

// project imports
import MainLayout from 'layout/MainLayout';
import Loadable from 'ui-component/Loadable';

// sample page routing
const SamplePage = Loadable(lazy(() => import('views/sample-page')));
const PositionsPage = Loadable(lazy(() => import('views/positions')));

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
    }
  ]
};

export default MainRoutes;

