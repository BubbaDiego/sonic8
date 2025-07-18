import { render, screen } from '@testing-library/react';
import { Provider } from 'react-redux';
import '@testing-library/jest-dom';
import { store } from 'store';
import { ConfigProvider } from 'contexts/ConfigContext';
import AlertThresholdsPage from 'views/alertThresholds/AlertThresholdsPage';

test('renders Alert Thresholds heading', () => {
  render(
    <Provider store={store}>
      <ConfigProvider>
        <AlertThresholdsPage />
      </ConfigProvider>
    </Provider>
  );
  expect(screen.getByText('Alert Thresholds')).toBeInTheDocument();
});
