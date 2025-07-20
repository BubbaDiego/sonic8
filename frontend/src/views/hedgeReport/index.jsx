import Loadable from 'ui-component/Loadable';
import { lazy } from 'react';

const HedgeReportPage = Loadable(lazy(() => import('./HedgeReportPage')));

export default HedgeReportPage;
