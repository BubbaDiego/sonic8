import React from 'react';
import { Avatar } from '@mui/material';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import CheckIcon from '@mui/icons-material/Check';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

/**
 * Single liquidation row.
 * Implements color logic:
 *   green if travel_percent > 10
 *   blue  if -10 <= travel_percent <= 10
 *   red   if travel_percent < -10
 */
const LiqRow = ({ pos }) => {
  const pct = Number(pos.travel_percent ?? 0);
  const direction = pct >= 0 ? 'positive' : 'negative';
  const width = Math.abs(pct) + '%';

  // determine color class for blue range
  const colorClass =
    pct > 10 ? 'green' :
    pct < -10 ? 'red' : 'blue';

  // badge logic
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
    <div className="liq-row">
      <a href={\`/launch/\${pos.chrome_profile || 'Default'}/\${pos.asset_type}\`}>
        <Avatar
          src={pos.wallet_image}
          alt={pos.wallet_name}
          sx={{
            width: 40,
            height: 40,
            border: pos.hedge_color ? \`4px solid \${pos.hedge_color}\` : '4px solid transparent'
          }}
        />
      </a>

      <div className="liq-progress-bar">
        <div className="liq-bar-container">
          <div className="liq-midline" />
          <div
            className={\`liq-bar-fill \${direction} \${colorClass}\`}
            style={direction === 'positive'
              ? { left: '50%', width }
              : { right: '50%', width }}
          >
            <div className="travel-text">{pct.toFixed(1)}%</div>
          </div>
        </div>

        <div className={\`liq-flame-container\${badgeClassExtra}\`}>
          {badgeContent}
        </div>
      </div>
    </div>
  );
};

export default LiqRow;
