import { useState, useMemo } from 'react';
import Stack from '@mui/material/Stack';
import PropTypes from 'prop-types';

import StatusCard from './StatusCard';
import { portfolioCards } from './cardData.jsx';

// data hooks
import { useGetLatestPortfolio } from 'api/portfolio';

/**
 * Horizontal rail of compact status cards.
 *
 * Any click toggles every card between its Portfolio (front) and Monitor (back) faces.
 */
export default function StatusRail({ cards = portfolioCards }) {
  const [monitorMode, setMonitorMode] = useState(false);

  // single source of truth for the toggle state
  const handleToggle = () => setMonitorMode((prev) => !prev);

  // fetch portfolio snapshot once – keeps component generic & testable
  const { portfolio } = useGetLatestPortfolio();

  // compute front‑face values only once per render
  const cardProps = useMemo(
    () =>
      cards.map((c) => ({
        ...c,
        value: c.selector({ portfolio })
      })),
    [cards, portfolio]
  );

  return (
    <Stack direction="row" spacing={2}>
      {cardProps.map((card) => (
        <StatusCard
          key={card.key}
          front={card}
          // ⬇️  monitor face will land in Phase 2
          back={<div style={{ fontSize: 12, opacity: 0.6 }}>Coming soon</div>}
          flipped={monitorMode}
          onToggle={handleToggle}
        />
      ))}
    </Stack>
  );
}

StatusRail.propTypes = { cards: PropTypes.array };