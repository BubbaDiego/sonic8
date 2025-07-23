import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import '@testing-library/jest-dom';
import { store } from 'store';
import { ConfigProvider } from 'contexts/ConfigContext';
import MonitorManager from 'views/monitorManager/MonitorManager';

test('renders Monitor Manager heading', () => {
  render(
    <Provider store={store}>
      <ConfigProvider>
        <MonitorManager />
      </ConfigProvider>
    </Provider>
  );
  expect(screen.getByText('Monitor Manager')).toBeInTheDocument();
});
