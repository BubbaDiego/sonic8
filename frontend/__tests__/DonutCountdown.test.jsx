import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import DonutCountdown from 'layout/MainLayout/Header/TimerSection/DonutCountdown';

describe('DonutCountdown', () => {
  test('renders number and label', () => {
    render(<DonutCountdown remaining={10} total={60} label="Next Sonic" />);
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('Next Sonic')).toBeInTheDocument();
  });

  test('shows completion icon when done', () => {
    render(<DonutCountdown remaining={0} total={60} label="Next Sonic" />);
    expect(screen.queryByText('0')).not.toBeInTheDocument();
    expect(screen.getByTestId('CheckCircleIcon')).toBeInTheDocument();
  });
});
