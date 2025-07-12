import { useState, useMemo } from 'react';
import Stack from '@mui/material/Stack';
import PropTypes from 'prop-types';

import StatCard from './StatCard';
import { portfolioCards } from './cardData.jsx';
import { useGetLatestPortfolio } from 'api/portfolio';

export default function StatusRail({ cards = portfolioCards }) {
  const [flippedCards, setFlippedCards] = useState({});

  const { portfolio } = useGetLatestPortfolio();

  const cardProps = useMemo(
    () =>
      cards.map((c) => ({
        ...c,
        value: c.selector({ portfolio }),
      })),
    [cards, portfolio]
  );

  const handleToggle = (key) => {
    setFlippedCards((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <Stack direction="row" spacing={2}>
      {cardProps.map((card) => (
        <StatCard
          key={card.key}
          icon={card.icon}
          label={card.label}
          value={card.value}
          secondary={card.secondary}
          variant={card.variant || 'light'}
          flipped={!!flippedCards[card.key]}
          onClick={() => handleToggle(card.key)}
        />
      ))}
    </Stack>
  );
}

StatusRail.propTypes = { cards: PropTypes.array };
