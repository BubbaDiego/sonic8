import { useQuery, useQueryClient } from '@tanstack/react-query';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Button, Typography } from '@mui/material';

async function http(path) {
  const res = await fetch(path);
  const txt = await res.text();
  let json = {};
  try { json = txt ? JSON.parse(txt) : {}; } catch {}
  if (!res.ok) throw new Error(json.detail || json.message || `HTTP ${res.status}`);
  return json;
}
const getOwner = () => http('/api/jupiter/whoami'); // { pubkey, signer: {...} }

const toNum = (v, d = null) => (v == null || v === '' || Number.isNaN(+v) ? d : Number(v));
const fmtN  = (v, dp) => (v == null ? '—' : Number(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: dp }));
const link  = (sig) => `https://solscan.io/account/${encodeURIComponent(sig)}`;

// read exactly the same source as the Positions page and shape for this table
const getFromDb = async (owner, limit) => {
  const arr = await http('/positions/');              // PositionDB[]
  const rows = Array.isArray(arr) ? arr : [];

  // Try to scope to the active signer. We’ll match common field names if present;
  // otherwise fall back to rows where wallet_name === 'Signer'. If no match, show all.
  const ownerLc = (owner || '').toLowerCase();
  const owned = rows.filter((r) => {
    const cands = [
      r?.wallet_pubkey, r?.owner, r?.wallet, r?.wallet_address, r?.public_address
    ].map((x) => (x || '').toString().toLowerCase());
    return (ownerLc && cands.some((x) => x === ownerLc)) || r?.wallet_name === 'Signer';
  });
  const useRows = owned.length > 0 ? owned : rows;

  const items = useRows.slice(0, limit || 100).map((r) => ({
    pubkey: r?.id ?? '',
    side: (r?.position_type || '').toLowerCase(),              // 'long' | 'short'
    size: toNum(r?.size, 0),
    entry: toNum(r?.entry_price, null),
    mark:  toNum(r?.current_price, null),
    pnlUsd: toNum(r?.pnl_after_fees_usd, 0)
  }));
  return { count: items.length, items };
};

export default function PositionsPanel() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey:['perpsWhoami'], queryFn:getOwner, staleTime:5000, retry:0 });
  const owner = me.data?.pubkey;
  const q = useQuery({
    queryKey:['perpsPositionsFromDb', owner],
    queryFn:()=>getFromDb(owner, 100),
    enabled: !!owner,
    staleTime: 3000,
    refetchInterval: 10000  // light auto-refresh; remove if you don't want it
  });

  return (
    <MainCard
      title="Perps · My Positions"
      secondary={<Button size="small" onClick={()=>qc.invalidateQueries({ queryKey:['perpsPositionsFromDb'] })}>Refresh</Button>}
    >
      {!q.isSuccess ? (
        <Typography>Loading…</Typography>
      ) : (
        <Box sx={{ fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12 }}>
          <Typography variant="body2" sx={{opacity:.85, mb:1}}>
            owner: <code>{owner}</code>
          </Typography>
          <div>count: {q.data.count ?? 0}</div>
          <hr />
          {(q.data.items||[]).length === 0 && <Typography>No open positions.</Typography>}
          {(q.data.items||[]).length > 0 && (
            <table width="100%" cellPadding="4" style={{borderCollapse:'collapse'}}>
              <thead>
                <tr>
                  <th align="left">Pubkey</th>
                  <th align="left">Side</th>
                  <th align="right">Size</th>
                  <th align="right">Entry</th>
                  <th align="right">Mark</th>
                  <th align="right">PnL ($)</th>
                </tr>
              </thead>
              <tbody>
                {q.data.items.map((r,i)=>{
                  const pnl = r.pnlUsd ?? 0;
                  const pnlStr = pnl >= 0 ? `+${fmtN(pnl, 2)}` : fmtN(pnl, 2);
                  const pnlColor = pnl > 0 ? '#22c55e' : pnl < 0 ? '#ef4444' : undefined;
                  return (
                    <tr key={i}>
                      <td>
                        {r.pubkey ? (
                          <a href={link(r.pubkey)} target="_blank" rel="noreferrer">
                            <code>{r.pubkey.slice(0,6)}…{r.pubkey.slice(-6)}</code>
                          </a>
                        ) : '—'}
                      </td>
                      <td style={{textTransform:'uppercase'}}>{r.side || '—'}</td>
                      <td align="right">{fmtN(r.size, 6)}</td>
                      <td align="right">{fmtN(r.entry, 3)}</td>
                      <td align="right">{fmtN(r.mark, 3)}</td>
                      <td align="right" style={{color: pnlColor}}>{pnlStr}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Box>
      )}
    </MainCard>
  );
}
