import React from 'react';
import { Avatar, Box } from '@mui/material';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import CheckIcon from '@mui/icons-material/Check';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

const LiqRow = ({ pos }) => {
  const pct = Number(pos.travel_percent ?? 0);
  const direction = pct >= 0 ? 'positive' : 'negative';
  const width = Math.min(Math.abs(pct), 100) + '%';  // Cap at 100%

  const colorClass =
    pct > 10 ? 'green' :
    pct < -10 ? 'red' : 'blue';

  const profit = Number(pos.pnl_after_fees_usd ?? 0);
  const heat = pos.heat_index != null ? Number(pos.heat_index) : null;
  const stale = Number(pos.stale ?? 0) > 0;

  let badgeContent = null;
  let badgeClassExtra = '';

  if (stale) {
    badgeContent = <HelpOutlineIcon fontSize="inherit" />;
  } else if (profit > 5) {
    badgeContent = <span className="profit-number">{Math.round(profit)}</span>;
    badgeClassExtra = ' profit';
  } else if (profit < 5 && heat != null && heat < 5.5) {
    badgeContent = <CheckIcon className="cold-check-icon" fontSize="inherit" />;
    badgeClassExtra = ' cold';
  } else {
    badgeContent = <span className="heat-index-number">{heat != null ? Math.round(heat) : 'N/A'}</span>;
  }

  return (
    <Box className="liq-row" sx={{ display: 'flex', alignItems: 'center', width: '100%', px: 2, py: 1 }}>
      <a href={`/launch/${pos.chrome_profile || 'Default'}/${pos.asset_type}`}>
        <Avatar
          src={pos.wallet_image}
          alt={pos.wallet_name}
          sx={{ width: 40, height: 40, border: pos.hedge_color ? `4px solid ${pos.hedge_color}` : '4px solid transparent' }}
        />
      </a>

      <Box className="liq-progress-bar" sx={{ position: 'relative', flex: 1, ml: 2, height: 20 }}>
        <Box className="liq-bar-container" sx={{ position: 'relative', width: '100%', height: '100%', bgcolor: '#eee', borderRadius: '10px', overflow: 'hidden' }}>
          <Box className="liq-midline" sx={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', bgcolor: '#555' }} />
          <Box
            className={`liq-bar-fill ${direction} ${colorClass}`}
            sx={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              left: direction === 'positive' ? '50%' : 'auto',
              right: direction === 'negative' ? '50%' : 'auto',
              width,
              display: 'flex',
              alignItems: 'center',
              justifyContent: direction === 'positive' ? 'flex-start' : 'flex-end',
              px: 1,
              color: '#fff',
              fontWeight: 'bold',
              bgcolor:
                colorClass === 'green' ? 'success.main' :
                colorClass === 'red' ? 'error.main' : 'info.main'
            }}
          >
            {pct.toFixed(1)}%
          </Box>
        </Box>

        <Box className={`liq-flame-container${badgeClassExtra}`} sx={{ position: 'absolute', top: '-10px', right: '-10px', bgcolor: 'orange', borderRadius: '50%', width: 24, height: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '0.75rem' }}>
          {badgeContent}
        </Box>
      </Box>
    </Box>
  );
};

export default LiqRow;
