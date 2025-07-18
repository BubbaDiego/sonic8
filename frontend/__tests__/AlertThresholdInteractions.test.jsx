import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { Provider } from 'react-redux';
import { store } from 'store';
import { ConfigProvider } from 'contexts/ConfigContext';
import Notistack from 'ui-component/third-party/Notistack';
import Snackbar from 'ui-component/extended/Snackbar';
import AlertThresholdsPage from 'views/alertThresholds/AlertThresholdsPage';

// Mock axios to track API calls
const axios = { put: jest.fn(), get: jest.fn() };
jest.mock('utils/axios', () => ({ __esModule: true, default: axios }));

// SWR mock with mutable data
let swrData = [];
let setData;
function useSWRMock() {
  const React = require('react');
  const [data, set] = React.useState(swrData);
  setData = set;
  return {
    data,
    mutate: jest.fn(() => {
      set(swrData);
      return Promise.resolve();
    })
  };
}
useSWRMock.__setData = (d) => {
  swrData = d;
  if (setData) setData(d);
};
jest.mock('swr', () => ({ __esModule: true, default: useSWRMock }));

function renderPage() {
  return render(
    <Provider store={store}>
      <ConfigProvider>
        <Notistack>
          <AlertThresholdsPage />
          <Snackbar />
        </Notistack>
      </ConfigProvider>
    </Provider>
  );
}

describe('AlertThresholdsPage interactions', () => {
  beforeEach(() => {
    axios.put.mockResolvedValue({});
    axios.get.mockResolvedValue({ data: { thresholds: [], monitorEnabled: true } });
    useSWRMock.__setData([]);
  });

  test('clicking Save calls bulk PUT', async () => {
    useSWRMock.__setData([{ id: 1, alert_type: 'Test' }]);
    renderPage();
    await userEvent.click(screen.getByTestId('save-btn'));
    expect(axios.put).toHaveBeenCalledWith('/alert_thresholds/bulk', {
      thresholds: [{ id: 1, alert_type: 'Test' }],
      monitorEnabled: true
    });
  });

  test('import json populates table and shows snackbar', async () => {
    renderPage();
    const file = new File([
      JSON.stringify({ thresholds: [{ id: 2, alert_type: 'Profit' }], monitorEnabled: true })
    ], 'import.json', { type: 'application/json' });

    axios.put.mockImplementation((url, body) => {
      useSWRMock.__setData(body.thresholds);
      return Promise.resolve({});
    });

    await userEvent.upload(screen.getByLabelText('Import'), file);

    await waitFor(() => expect(screen.getByText('Profit')).toBeInTheDocument());
    expect(screen.getByText('Configuration imported')).toBeInTheDocument();
  });

  test('export downloads json', async () => {
    useSWRMock.__setData([]);
    axios.get.mockResolvedValue({ data: { thresholds: [{ id: 3 }] } });
    const urlSpy = jest.spyOn(URL, 'createObjectURL').mockReturnValue('blob:1');
    const revokeSpy = jest.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    const clickMock = jest.fn();
    jest.spyOn(document, 'createElement').mockReturnValue({ click: clickMock, set href(v) {}, set download(v) {} });

    renderPage();
    await userEvent.click(screen.getByTestId('export-btn'));

    expect(axios.get).toHaveBeenCalledWith('/alert_thresholds/bulk');
    expect(urlSpy).toHaveBeenCalled();
    expect(clickMock).toHaveBeenCalled();

    urlSpy.mockRestore();
    revokeSpy.mockRestore();
  });
});
