import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import PositionTableCard from 'views/positions/PositionTableCard';

// Mock axios used by the component
const axios = { get: jest.fn() };
jest.mock('utils/axios', () => ({ __esModule: true, default: axios }));

function mockPositions() {
  return [
    { id: 1, wallet_name: 'Wallet1', asset_type: 'BTC', position_type: 'LONG', size: 1, value: 100, collateral: 50 },
    { id: 2, wallet_name: 'Wallet2', asset_type: 'ETH', position_type: 'SHORT', size: 2, value: 200, collateral: 80 }
  ];
}

describe('PositionTableCard', () => {
  beforeEach(() => {
    axios.get.mockResolvedValue({ data: mockPositions() });
  });

  test('renders fetched rows and totals', async () => {
    render(<PositionTableCard />);
    expect(axios.get).toHaveBeenCalledWith('/positions/');

    await waitFor(() => expect(screen.getByText('Portfolio Positions')).toBeInTheDocument());

    expect(screen.getByText('Wallet1')).toBeInTheDocument();
    expect(screen.getByText('Wallet2')).toBeInTheDocument();
    expect(screen.getByText('Totals')).toBeInTheDocument();
    expect(screen.getByText('$300')).toBeInTheDocument();
    expect(screen.getByText('$130')).toBeInTheDocument();
  });

  test('clicking column header sorts rows', async () => {
    render(<PositionTableCard />);
    await screen.findByText('Wallet1');

    const valueHeader = screen.getByRole('button', { name: /Value/i });
    await userEvent.click(valueHeader);

    const rows = screen.getAllByRole('row');
    // first data row after header should be wallet1 (100 < 200)
    expect(rows[1]).toHaveTextContent('Wallet1');
  });
});
