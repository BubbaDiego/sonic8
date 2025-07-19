// src/components/PortfolioBar.jsx
import Stack from '@mui/material/Stack';
import Box from '@mui/material/Box';

import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import LocalFireDepartmentTwoToneIcon from '@mui/icons-material/LocalFireDepartmentTwoTone';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';
import Inventory2TwoToneIcon from '@mui/icons-material/Inventory2TwoTone';

import StatCard from './StatCard';

function formatValue(v) {
  return v != null
    ? `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
    : '--';
}
function formatHeat(v) {
  return v != null ? Number(v).toFixed(2) : '--';
}
function formatLeverage(v) {
  return v != null ? Number(v).toFixed(2) : '--';
}
function formatSize(v) {
  return v != null ? `${(Number(v) / 1_000).toFixed(1)}k` : '--';
}

export default function PortfolioBar({ data = {}, variant = 'light', onToggle }) {
  const cards = [
    {
      key: 'value',
      label: 'Value',
      value: formatValue(data.value),
      icon: <MonetizationOnTwoToneIcon />
    },
    {
      key: 'heat',
      label: 'Heat',
      value: formatHeat(data.heatIndex),
      icon: <LocalFireDepartmentTwoToneIcon />
    },
    {
      key: 'leverage',
      label: 'Leverage',
      value: formatLeverage(data.leverage),
      icon: <TrendingUpTwoToneIcon />
    },
    {
      key: 'size',
      label: 'Size',
      value: formatSize(data.size),
      icon: <Inventory2TwoToneIcon />
    }
  ];

  return (
    <Stack
      direction="row"
      spacing={2}
      sx={{ width: '100%', flexWrap: 'nowrap', alignItems: 'stretch' }}
    >
      {cards.map((c) => (
        <Box key={c.key} sx={{ flex: 1, minWidth: 0 }}>
          <StatCard
            variant={variant}
            label={c.label}
            value={c.value}
            icon={c.icon}
            onClick={onToggle}
          />
        </Box>
      ))}
    </Stack>
  );
}
