import React, { useMemo } from 'react';
import AssetLogo from './AssetLogo';         // ← same component used in Liquidation card
import {
  Card, CardHeader, CardContent,
  Table, TableHead, TableBody, TableRow, TableCell,
  TextField, Typography
} from '@mui/material';

export default function MarketMovementCard({ cfg, setCfg, live }) {
  const ASSETS  = ['SPX', 'BTC', 'ETH', 'SOL'];
  const WINDOWS = ['1h', '6h', '24h'];      // trimmed columns

  const norm = useMemo(() => {
    const t = cfg.thresholds || {};
    return Object.fromEntries(
      ASSETS.map(a => [
        a,
        WINDOWS.reduce((o, w) => ({ ...o, [w]: t?.[a]?.[w] ?? '' }), {})
      ])
    );
  }, [cfg]);

  const onChange = (asset, win) => e =>
    setCfg(p => ({
      ...p,
      thresholds: {
        ...p.thresholds,
        [asset]: { ...(p.thresholds?.[asset] || {}), [win]: e.target.value }
      }
    }));

  return (
    <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardHeader title="Market Monitor (intra-day)" />
      <CardContent sx={{ p: 0 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Asset</TableCell>
              {WINDOWS.map(w => (
                <TableCell key={w} align="center">{w}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {ASSETS.map(a => (
              <TableRow key={a}>
                <TableCell>
                  <AssetLogo symbol={a} size={20}/>
                </TableCell>
                {WINDOWS.map(w => (
                  <TableCell key={w} align="center">
                    <TextField
                      type="number"
                      size="small"
                      value={norm[a][w]}
                      onChange={onChange(a, w)}
                      sx={{ width: 72, mb: .5 }}
                    />
                    {(() => {
                      const pct = live?.[a]?.[w]?.pct_move;
                      const colour =
                        pct == null
                          ? 'text.secondary'
                          : Math.abs(pct) > 100
                            ? 'success.main'      // > 100 % → green
                            : Math.abs(pct) > 50
                              ? 'warning.main'    // 50‑100 % → yellow
                              : 'error.main';     // < 50 % → red
                      return (
                        <Typography
                          variant="caption"
                          sx={{ fontWeight: 700 }}
                          color={colour}
                        >
                          {pct != null ? `(${pct.toFixed(2)}%)` : '—'}
                        </Typography>
                      );
                    })()}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
