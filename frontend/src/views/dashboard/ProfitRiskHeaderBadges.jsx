// material-ui
import { Stack, Typography, Avatar, Box, Tooltip } from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

// canned demo data
const profitLeader = {
  walletIcon: 'https://cryptologos.cc/logos/solana-sol-logo.png',
  profit: 1234.56
};

const highestRisk = {
  walletIcon: 'https://cryptologos.cc/logos/ethereum-eth-logo.png',
  travelPercent: -42.8
};

const badgeStyle = {
  display: 'flex',
  alignItems: 'center',
  bgcolor: 'background.paper',
  borderRadius: 2,
  boxShadow: 2,
  px: 1,
  py: 0.5,
  minWidth: 120
};

export default function ProfitRiskHeaderBadges() {
  return (
    <Stack direction="row" spacing={1}>
      {/* profit badge */}
      <Tooltip title="Most Profitable Position">
        <Box sx={{ ...badgeStyle, borderLeft: '4px solid', borderColor: 'success.main' }}>
          <Avatar src={profitLeader.walletIcon} sx={{ width: 24, height: 24, mr: 0.5 }} />
          <Typography variant="subtitle2" color="success.main" sx={{ fontWeight: 'bold' }}>
            ${profitLeader.profit.toFixed(2)}
          </Typography>
          <TrendingUpIcon sx={{ color: 'success.main', ml: 0.5, fontSize: 20 }} />
        </Box>
      </Tooltip>

      {/* risk badge */}
      <Tooltip title="Riskiest Position">
        <Box sx={{ ...badgeStyle, borderLeft: '4px solid', borderColor: 'error.main' }}>
          <Avatar src={highestRisk.walletIcon} sx={{ width: 24, height: 24, mr: 0.5 }} />
          <Typography variant="subtitle2" color="error.main" sx={{ fontWeight: 'bold' }}>
            {highestRisk.travelPercent.toFixed(1)}%
          </Typography>
          <WarningAmberIcon sx={{ color: 'error.main', ml: 0.5, fontSize: 20 }} />
        </Box>
      </Tooltip>
    </Stack>
  );
}
