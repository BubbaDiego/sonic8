import { createBrowserRouter } from 'react-router-dom';

// error boundary
import ErrorBoundary from './ErrorBoundary.jsx';

// routes
import AuthenticationRoutes from './AuthenticationRoutes';
import MainRoutes from './MainRoutes';
import TraderShopRoutes from './TraderShopRoutes';
import ErrorBoundary from './ErrorBoundary';

// ==============================|| ROUTING RENDER ||============================== //

const router = createBrowserRouter([MainRoutes, TraderShopRoutes, AuthenticationRoutes], {
  basename: import.meta.env.VITE_APP_BASE_NAME,
  errorElement: <ErrorBoundary />
});

export default router;
