import { render } from '@testing-library/react';
import SonicReactApp from '../SonicReactApp';

test('SonicReactApp mounts without crashing', () => {
  expect(() => render(<SonicReactApp />)).not.toThrow();
});
