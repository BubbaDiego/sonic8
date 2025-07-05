import Loadable from 'ui-component/Loadable';
import { lazy } from 'react';

const AlertThresholdsPage = Loadable(lazy(() => import('./AlertThresholdsPage')));

export default AlertThresholdsPage;
