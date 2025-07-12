import PaidTwoToneIcon       from '@mui/icons-material/PaidTwoTone';
import WhatshotTwoToneIcon   from '@mui/icons-material/WhatshotTwoTone';
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';
import InventoryTwoToneIcon  from '@mui/icons-material/InventoryTwoTone';

/**
 * Pure data description of cards shown in Portfolio mode.
 * The `selector` reads the desired metric from the latest portfolio snapshot.
 */
export const portfolioCards = [
  {
    key: 'value',
    label: 'Value',
    icon: <PaidTwoToneIcon fontSize="small" />,
    color: 'primary',
    selector: ({ portfolio }) =>
      portfolio?.total_value !== undefined
        ? `$${portfolio.total_value.toFixed(1)}`
        : '--'
  },
  {
    key: 'heat',
    label: 'Heat',
    icon: <WhatshotTwoToneIcon fontSize="small" />,
    color: 'error',
    selector: ({ portfolio }) =>
      portfolio?.avg_heat_index !== undefined
        ? portfolio.avg_heat_index.toFixed(2)
        : '--'
  },
  {
    key: 'leverage',
    label: 'Leverage',
    icon: <TrendingUpTwoToneIcon fontSize="small" />,
    color: 'info',
    selector: ({ portfolio }) =>
      portfolio?.avg_leverage !== undefined
        ? portfolio.avg_leverage.toFixed(2)
        : '--'
  },
  {
    key: 'size',
    label: 'Size',
    icon: <InventoryTwoToneIcon fontSize="small" />,
    color: 'warning',
    selector: ({ portfolio }) =>
      portfolio?.total_size !== undefined
        ? `${(portfolio.total_size / 1_000).toFixed(1)}k`
        : '--'
  }
];