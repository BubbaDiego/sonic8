import { lazy } from 'react';

// project imports
import Loadable from 'ui-component/Loadable';
import MinimalLayout from 'layout/MinimalLayout';

// login pages are removed

// maintenance routing
const MaintenanceError = Loadable(lazy(() => import('views/pages/maintenance/Error')));
const MaintenanceError500 = Loadable(lazy(() => import('views/pages/maintenance/Error500')));
const MaintenanceComingSoon1 = Loadable(lazy(() => import('views/pages/maintenance/ComingSoon/ComingSoon1')));
const MaintenanceComingSoon2 = Loadable(lazy(() => import('views/pages/maintenance/ComingSoon/ComingSoon2')));
const MaintenanceUnderConstruction = Loadable(lazy(() => import('views/pages/maintenance/UnderConstruction')));

// landing & contact-us routing
const PagesLanding = Loadable(lazy(() => import('views/pages/landing')));

// ==============================|| AUTHENTICATION ROUTING ||============================== //

const AuthenticationRoutes = {
  path: '/',
  element: <MinimalLayout />,
  children: [
    {
      path: '/pages/error',
      element: <MaintenanceError />
    },
    {
      path: '/pages/500',
      element: <MaintenanceError500 />
    },
    {
      path: '/pages/coming-soon1',
      element: <MaintenanceComingSoon1 />
    },
    {
      path: '/pages/coming-soon2',
      element: <MaintenanceComingSoon2 />
    },
    {
      path: '/pages/under-construction',
      element: <MaintenanceUnderConstruction />
    },

    {
      path: '/pages/landing',
      element: <PagesLanding />
    }
  ]
};

export default AuthenticationRoutes;
