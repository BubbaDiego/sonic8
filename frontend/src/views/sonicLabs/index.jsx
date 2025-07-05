import Loadable from 'ui-component/Loadable';
import { lazy } from 'react';

const SonicLabsPage = Loadable(lazy(() => import('./SonicLabsPage')));

export default SonicLabsPage;
