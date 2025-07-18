import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import PortfolioSessionCard from 'components/PortfolioSessionCard/PortfolioSessionCard';

const baseSnapshot = {
  session_start_time: new Date('2024-01-02T03:04:05Z'),
  session_start_value: 123,
  session_goal_value: 200,
  current_total_value: 150,
  session_performance_value: 27
};

function makeSnapshot() {
  return { ...baseSnapshot };
}

test('renders date, time and start amount', () => {
  const snapshot = makeSnapshot();
  render(<PortfolioSessionCard snapshot={snapshot} />);
  const d = new Date(snapshot.session_start_time);
  const dateStr = `${d.getMonth() + 1}/${d.getDate()}`;
  const timeStr = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  expect(screen.getByText(dateStr)).toBeInTheDocument();
  expect(screen.getByText(timeStr)).toBeInTheDocument();
  expect(screen.getByText(/123/)).toBeInTheDocument();
});

test('calls onEditStart when edit icon clicked', async () => {
  const snapshot = makeSnapshot();
  const onEditStart = jest.fn();
  render(<PortfolioSessionCard snapshot={snapshot} onEditStart={onEditStart} />);
  await userEvent.click(screen.getByTestId('edit-btn'));
  expect(onEditStart).toHaveBeenCalled();
});
