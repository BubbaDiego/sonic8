import React, { useMemo } from 'react';
import {
  Card, CardHeader, CardContent,
  Table, TableHead, TableBody, TableRow, TableCell,
  TextField, Typography
} from '@mui/material';

export default function MarketMovementCard({ cfg, setCfg, live }) {
  const ASSETS  = ['SPX', 'BTC', 'ETH', 'SOL'];
  const WINDOWS = ['15m', '1h', '3h', '6h', '12h', '24h'];

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
                <TableCell>{a}</TableCell>
                {WINDOWS.map(w => (
                  <TableCell key={w} align="center">
                    <TextField
                      type="number"
                      size="small"
                      value={norm[a][w]}
                      onChange={onChange(a, w)}
                      sx={{ width: 72, mb: .5 }}
                    />
                    <Typography
                      variant="caption"
                      color={
                        Math.abs(live?.[a]?.[w]?.pct_move || 0) >= (norm[a][w] || 0)
                          ? 'error.main'
                          : 'text.secondary'
                      }
                    >
                      {live?.[a]?.[w]?.pct_move?.toFixed(2) ?? '—'}%
                    </Typography>
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
