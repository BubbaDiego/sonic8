import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ThresholdTable from 'ui-component/thresholds/ThresholdTable';

describe('ThresholdTable', () => {
  test('renders rows and triggers onChange', async () => {
    const handleChange = jest.fn();
    const rows = [
      { id: '1', alert_type: 'Price', alert_class: 'Position', condition: 'ABOVE', metric_key: 'price', low: 1, medium: 2, high: 3, enabled: true }
    ];

    render(<ThresholdTable rows={rows} onChange={handleChange} />);

    expect(screen.getByText('alert_type')).toBeInTheDocument();
    expect(screen.getByDisplayValue('1')).toBeInTheDocument();

    const input = screen.getByDisplayValue('1');
    await userEvent.clear(input);
    await userEvent.type(input, '10');
    expect(handleChange).toHaveBeenLastCalledWith('1', 'low', 10);
  });
});
