import Loadable from 'ui-component/Loadable';
import { lazy } from 'react';

const PositionsPage = Loadable(lazy(() => import('./PositionsPage')));

export default PositionsPage;

