// frontend/src/views/jupiter/JupiterPage.jsx
import { useState, useMemo, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { enqueueSnackbar } from 'notistack';

import MainCard from 'ui-component/cards/MainCard';
import {
  // swaps + helpers
  swapQuote, swapExecute, getUsdPrice,
  // wallet & portfolio
  whoami, signerInfo, walletPortfolio, estimateSolSpend,
  // txlog (projected vs actual profit)
  txlogLatest, txlogList,
  // sending
  sendToken
} from 'api/jupiter';

import {
  Box, Button, Chip, Grid, Stack, Tab, Tabs, TextField, Typography,
  MenuItem, FormControlLabel, Switch, Divider, Tooltip, IconButton
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import MarketsPanel from 'components/jupiter/Perps/MarketsPanel';
import PositionsPanel from 'components/jupiter/Perps/PositionsPanel';

/* ------------------------------------------------------------------ */
/* Token directory                                                     */
/* ------------------------------------------------------------------ */
const TOKENS = [
  { sym: 'SOL',     mint: 'So11111111111111111111111111111111111111112', decimals: 9 },
  { sym: 'USDC',    mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', decimals: 6 },
  { sym: 'mSOL',    mint: 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',  decimals: 9 },
  { sym: 'JitoSOL', mint: 'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', decimals: 9 }
];
const sym = (s) => TOKENS.find((t) => t.sym === s);

/* helpers */
const atomsToUi = (atoms, decimals) => Number(atoms || 0) / 10 ** decimals;
const fmt = (n, dp = 6) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: dp });
const pct = (x) => (Number(x || 0) * 100).toLocaleString(undefined, { maximumFractionDigits: 4 }) + '%';

/* ------------------------------------------------------------------ */
/* Send Tokens card                                                    */
/* ------------------------------------------------------------------ */
function SendCard({ onLog }) {
  const [mintSym, setMintSym] = useState('USDC');
  const [to, setTo] = useState('');
  const [amtUi, setAmtUi] = useState('');
  const [sending, setSending] = useState(false);
  const [usd, setUsd] = useState(null);

  const tok = sym(mintSym);
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const r = await getUsdPrice(tok.mint, 'USDC');
        if (live) setUsd(Number(r.price));
      } catch {
        if (live) setUsd(null);
      }
    })();
    return () => { live = false; };
  }, [mintSym]);

  const amtUsd = usd ? (Number(amtUi || 0) * usd) : null;

  const doSend = async () => {
    try {
      setSending(true);
      const atoms = Math.floor(Number(amtUi || 0) * 10 ** tok.decimals);
      if (!to || !atoms || atoms <= 0) {
        enqueueSnackbar('Enter recipient and amount', { variant: 'warning' });
        return;
      }
      onLog?.(`Send: ${mintSym} ${amtUi} → ${to}`);
      const r = await sendToken({ mint: tok.mint, to, amountAtoms: atoms });
      enqueueSnackbar('Send submitted', { variant: 'success' });
      onLog?.(`Send sent: ${r.signature}`, 'success');
    } catch (e) {
      const msg = e?.message || String(e);
      enqueueSnackbar(msg, { variant: 'error' });
      onLog?.(`Send error: ${msg}`, 'error');
    } finally {
      setSending(false);
    }
  };

  return (
    <MainCard title="Send Tokens">
      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Token" value={mintSym} onChange={(e)=>setMintSym(e.target.value)}>
            {TOKENS.map((t) => <MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} md={5}>
          <TextField fullWidth label="Recipient (pubkey)" placeholder="8h1… or CofTL…" value={to} onChange={(e)=>setTo(e.target.value)} />
        </Grid>
        <Grid item xs={12} md={2}>
          <TextField
            fullWidth label="Amount"
            value={amtUi} onChange={(e)=>setAmtUi(e.target.value)}
            helperText={amtUsd != null ? `≈ $${amtUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : ' '}
          />
        </Grid>
        <Grid item xs={12} md={2}>
          <Button fullWidth variant="contained" onClick={doSend} disabled={sending}>
            {sending ? 'Sending…' : 'Send'}
          </Button>
        </Grid>
      </Grid>
      <Typography variant="caption" color="textSecondary">
        If the recipient doesn’t have an ATA for this mint, we’ll create it automatically (uses a small amount of SOL).
      </Typography>
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Stubs for the other tabs                                            */
/* ------------------------------------------------------------------ */
function SpotTriggerForm() { return null; }
function SpotTriggerTable() { return null; }

/* ------------------------------------------------------------------ */
/* Wallet Card (multi-token + green USD)                               */
/* ------------------------------------------------------------------ */
function WalletCard() {
  const qc = useQueryClient();
  const who  = useQuery({ queryKey: ['jupWho'],        queryFn: whoami,        staleTime: 5000,  retry: 0 });
  const sinf = useQuery({ queryKey: ['jupSignerInfo'], queryFn: signerInfo,    staleTime: 10000, retry: 0 });

  const mintsCsv = TOKENS.map(t => t.mint).join(',');
  const portfolio = useQuery({
    queryKey: ['jupPortfolio'],
    queryFn: () => walletPortfolio(mintsCsv),
    staleTime: 5000,
    retry: 0,
    enabled: !!who.data
  });

  const short = (s) => (s ? `${s.slice(0,4)}…${s.slice(-4)}` : '');
  const pub   = who.data?.pubkey || sinf.data?.pubkey;

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['jupWho'] });
    qc.invalidateQueries({ queryKey: ['jupSignerInfo'] });
    qc.invalidateQueries({ queryKey: ['jupPortfolio'] });
  };

  const green = { color: 'var(--mui-palette-success-main, #2e7d32)', fontWeight: 600 };

  return (
    <MainCard title="Wallet" secondary={<Button size="small" onClick={refresh}>Refresh</Button>}>
      {!who.data ? (
        <Typography>Loading…</Typography>
      ) : portfolio.isError ? (
        <Typography color="error">Portfolio error: {portfolio.error?.message || 'unknown'}</Typography>
      ) : portfolio.isLoading ? (
        <Typography>Loading balances…</Typography>
      ) : (
        <Stack spacing={1}>
          <Typography variant="body2">Pubkey: <code>{short(pub)}</code></Typography>
          {portfolio.data?.items?.map((it) => {
            const usdValue = it.usd ?? it.amount;
            const usdText = usdValue == null ? '—' : `$${usdValue.toFixed(2)}`;
            return (
              <Typography key={it.mint} variant="body2">
                {it.sym}: <b>{fmt(it.amount)}</b>{' '}
                <span style={green}>({usdText})</span>
              </Typography>
            );
          })}
          <Typography variant="caption" color="textSecondary">
            Method: {sinf.data?.method || 'unknown'} — Path: {sinf.data?.path || ''}
          </Typography>
          {sinf.data?.note && <Typography variant="caption" color="textSecondary">Note: {sinf.data.note}</Typography>}
        </Stack>
      )}
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Quote + Round-trip panel (edge pill + details + tooltips)           */
/* ------------------------------------------------------------------ */
function QuoteCard({ quote, rt, inSym, outSym }) {
  const inDec  = sym(inSym).decimals;
  const outDec = sym(outSym).decimals;

  const pill = (() => {
    if (!rt) return { text: 'no edge', color: 'default', tip: 'No round-trip computed yet.' };
    const e = rt.edgeBps ?? 0;
    const tip = `Round-trip edge = ((B→A minOut) − initial A) / initial A × 10,000 bps. Positive = profit, negative = loss.`;
    if (e >= 50) return { text: `profit +${e.toFixed(2)} bps`, color: 'success', tip };
    if (e >= 0)  return { text: `near +${e.toFixed(2)} bps`,   color: 'warning', tip };
    return { text: `${e.toFixed(2)} bps`, color: 'error', tip };
  })();

  const Pill = (
    <Tooltip title={pill.tip}>
      <Chip color={pill.color} label={pill.text} />
    </Tooltip>
  );

  return (
    <MainCard title="Quote" secondary={Pill}>
      {quote ? (
        <Stack spacing={0.75}>
          <Stack direction="row" alignItems="center" spacing={0.5}>
            <Typography variant="body2">
              outAmount (atoms): <b>{quote.outAmount}</b>{' '}
              <span style={{ opacity: 0.8 }}>
                ({fmt(atomsToUi(quote.outAmount, outDec))} {outSym})
              </span>
            </Typography>
            <Tooltip title="Estimated output for A→B at quote time (not guaranteed by slippage).">
              <IconButton size="small"><InfoOutlinedIcon fontSize="inherit" /></IconButton>
            </Tooltip>
          </Stack>

          <Stack direction="row" alignItems="center" spacing={0.5}>
            <Typography variant="body2">
              otherAmountThreshold: <b>{quote.otherAmountThreshold}</b>{' '}
              <span style={{ opacity: 0.8 }}>
                ({fmt(atomsToUi(quote.otherAmountThreshold, outDec))} {outSym})
              </span>
            </Typography>
            <Tooltip title="Guaranteed min-out for A→B given your slippage (we rely on this).">
              <IconButton size="small"><InfoOutlinedIcon fontSize="inherit" /></IconButton>
            </Tooltip>
          </Stack>

          <Stack direction="row" alignItems="center" spacing={0.5}>
            <Typography variant="body2">priceImpactPct: <b>{pct(quote.priceImpactPct)}</b></Typography>
            <Tooltip title="Single-leg price impact for A→B (not the round-trip edge).">
              <IconButton size="small"><InfoOutlinedIcon fontSize="inherit" /></IconButton>
            </Tooltip>
          </Stack>

          {rt && (
            <>
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle2">Round-trip (A→B→A) analysis</Typography>
              <Typography variant="body2">
                A→B minOut (B): <b>{rt.a2bMinOut}</b>{' '}
                <span style={{ opacity: 0.8 }}>({fmt(atomsToUi(rt.a2bMinOut, outDec))} {outSym})</span>
              </Typography>
              <Typography variant="body2">
                B→A minOut (A): <b>{rt.b2aMinOut}</b>{' '}
                <span style={{ opacity: 0.8 }}>({fmt(atomsToUi(rt.b2aMinOut, inDec))} {inSym})</span>
              </Typography>
              <Typography variant="body2">
                Edge: <b>{(rt.edgeTokens ?? 0).toLocaleString()}</b> atoms of {inSym} (~ ${fmt(rt.edgeUsd ?? 0, 3)})
              </Typography>
              <Typography variant="caption" color="textSecondary">
                Uses <b>strict minOut</b> on both legs; sequential, not atomic (may fail if price moves).
              </Typography>
            </>
          )}
        </Stack>
      ) : (
        <Typography variant="body2" color="textSecondary">No quote yet.</Typography>
      )}
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Transaction card (Live / Details / History)                         */
/* ------------------------------------------------------------------ */
function TransactionCard({ log, onClear, onCopy }) {
  const [tab, setTab] = useState(0);
  const boxRef = useRef(null);
  useEffect(() => { if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight; }, [log]);

  const latest  = useQuery({ queryKey: ['txlogLatest'], queryFn: txlogLatest, staleTime: 0, retry: 0 });
  const history = useQuery({ queryKey: ['txlogList'],   queryFn: () => txlogList(25), staleTime: 0, retry: 0 });

  return (
    <MainCard
      title="Transaction"
      secondary={<Stack direction="row" spacing={1}><Button size="small" onClick={onCopy}>Copy</Button><Button size="small" onClick={onClear}>Clear</Button></Stack>}
    >
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 1 }}>
        <Tab label="Live log" /><Tab label="Details" /><Tab label="History" />
      </Tabs>

      {tab === 0 && (
        <Box ref={boxRef} sx={{ fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12, lineHeight:1.4, maxHeight:220, overflowY:'auto', p:1, bgcolor:'background.default', borderRadius:1, border:(t)=>`1px solid ${t.palette.divider}` }}>
          {log.length === 0
            ? <Typography variant="body2" color="textSecondary">No activity yet.</Typography>
            : log.map((r,i)=>(<div key={i} style={{whiteSpace:'pre-wrap'}}><span style={{color:'#888'}}>{r.ts}</span> <b>[{r.level}]</b> <span>{r.msg}</span></div>))}
        </Box>
      )}

      {tab === 1 && (
        latest.isLoading ? <Typography>Loading…</Typography> :
        latest.isError   ? <Typography color="error">No recent transaction</Typography> :
        <Box sx={{ fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12 }}>
          <Typography variant="body2"><b>Signature:</b> {latest.data.signature || latest.data.execution?.sig}</Typography>
          <Divider sx={{ my: 1 }} />
          <Typography variant="subtitle2">Projected</Typography>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(latest.data.projection, null, 2)}</pre>
          <Typography variant="subtitle2">Actual</Typography>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(latest.data.actual, null, 2)}</pre>
          <Typography variant="subtitle2">Execution</Typography>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(latest.data.execution, null, 2)}</pre>
        </Box>
      )}

      {tab === 2 && (
        history.isLoading ? <Typography>Loading…</Typography> :
        history.isError   ? <Typography color="error">History unavailable</Typography> :
        <Box sx={{ maxHeight: 240, overflowY: 'auto' }}>
          <table style={{ width: '100%', fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12 }}>
            <thead>
              <tr><th align="left">Time</th><th align="left">Pair</th><th align="right">Proj bps</th><th align="right">Act bps</th><th align="right">Act USD</th><th align="left">Sig</th></tr>
            </thead>
            <tbody>
              {(history.data.items || []).map((e,i)=>{
                const ts  = new Date(e.ts || Date.now()).toLocaleTimeString();
                const prb = e.projection?.edge?.bps ?? null;
                const acb = e.actual?.edge?.bps ?? null;
                const usd = e.actual?.pnlUsd;
                return (
                  <tr key={i}>
                    <td>{ts}</td>
                    <td>{e.pair?.in}→{e.pair?.out}</td>
                    <td align="right">{prb != null ? prb.toFixed(2) : '—'}</td>
                    <td align="right">{acb != null ? acb.toFixed(2) : '—'}</td>
                    <td align="right">{usd != null ? usd.toFixed(3) : '—'}</td>
                    <td>{(e.execution?.sig || '').slice(0, 6)}…</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Box>
      )}
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Swaps (headless) with Safe Max + Round-trip detector + Tx log       */
/* ------------------------------------------------------------------ */
function SwapsTab() {
  const queryClient = useQueryClient();

  const [inSym, setInSym]       = useState('SOL');
  const [outSym, setOutSym]     = useState('USDC');
  const [amountUi, setAmountUi] = useState('0.1');
  const [slip, setSlip]         = useState('50');
  const [mode, setMode]         = useState('ExactIn');
  const [restrict, setRestrict] = useState(true);
  const [thresh, setThresh]     = useState(50);

  const [quote, setQuote] = useState(null);
  const [rt, setRt]       = useState(null);
  const [sig, setSig]     = useState('');
  const [sending, setSending] = useState(false);

  const [usdPrice, setUsdPrice] = useState(null);
  useEffect(() => {
    let alive = true;
    const t = setTimeout(async () => {
      try { const r = await getUsdPrice(sym(inSym).mint, 'USDC'); if (alive) setUsdPrice(Number(r.price)); }
      catch { if (alive) setUsdPrice(null); }
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [inSym]);
  const amountUsd = (() => { const a = Number(amountUi || 0); return usdPrice ? a * usdPrice : null; })();

  const [txLog, setTxLog] = useState([]);
  const pushLog = (msg, level = 'info') => setTxLog((p) => [...p, { ts: new Date().toLocaleTimeString(), level, msg }]);

  const [est, setEst] = useState(null);
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        if (inSym !== 'SOL') { setEst(null); return; }
        pushLog(`Estimating safe SOL spend for OUT=${outSym}…`);
        const e = await estimateSolSpend(sym(outSym).mint);
        if (alive) { setEst(e); pushLog(`Est: safeMax=${e.safeMaxSol.toFixed(6)} SOL, needOutAta=${e.needOutAta}`); }
      } catch (err) { pushLog(`Estimator error: ${err?.message || String(err)}`, 'error'); if (alive) setEst(null); }
    })();
    return () => { alive = false; };
  }, [inSym, outSym]);

  const overMax = est && inSym === 'SOL' && Number(amountUi || 0) > (est.safeMaxSol || 0);
  const setMax  = () => {
    if (est?.safeMaxSol) {
      const v = Math.max(0, est.safeMaxSol - 0.0005);
      setAmountUi(v.toFixed(6));
      enqueueSnackbar(`Set to safe max: ${v.toFixed(6)} SOL`, { variant: 'info' });
    }
  };

  async function computeRoundTrip(a2bQuote, amountAtoms) {
    try {
      const aSym = inSym, bSym = outSym;
      const bMinOutAtoms = Number(a2bQuote.otherAmountThreshold);
      pushLog(`RT: reverse quote ${bSym}→${aSym} amount=${bMinOutAtoms} atoms…`);
      const back = await swapQuote({
        inputMint: sym(bSym).mint, outputMint: sym(aSym).mint,
        amount: bMinOutAtoms, slippageBps: Number(slip || 50), swapMode: 'ExactIn', restrictIntermediates: restrict
      });
      const aBackMinOutAtoms = Number(back.otherAmountThreshold);
      const edgeTokens = aBackMinOutAtoms - Number(amountAtoms);
      const edgeBps = (edgeTokens / Number(amountAtoms)) * 10_000;
      const edgeUsd = usdPrice ? (edgeTokens / (10 ** sym(aSym).decimals)) * usdPrice : 0;
      setRt({ a2bMinOut: bMinOutAtoms, b2aMinOut: aBackMinOutAtoms, edgeTokens, edgeBps, edgeUsd });
      pushLog(`RT: edge=${edgeBps.toFixed(2)} bps (~$${(edgeUsd || 0).toFixed(3)})`);
    } catch (e) {
      setRt(null);
      pushLog(`RT error: ${e?.message || String(e)}`, 'error');
    }
  }

  async function doQuote() {
    try {
      setSig(''); setQuote(null); setRt(null);
      const amtAtoms = Math.floor(Number(amountUi) * 10 ** sym(inSym).decimals);
      pushLog(`Quote: ${inSym}→${outSym}, amt=${amountUi} (${amtAtoms} atoms), slip=${slip}bps, restrict=${restrict}`);
      const q = await swapQuote({
        inputMint: sym(inSym).mint, outputMint: sym(outSym).mint,
        amount: amtAtoms, slippageBps: Number(slip || 50), swapMode: mode, restrictIntermediates: restrict
      });
      setQuote(q); pushLog(`Quote OK: out=${q.outAmount}, minOut=${q.otherAmountThreshold}, impact=${q.priceImpactPct}`);
      await computeRoundTrip(q, amtAtoms);
    } catch (e) {
      pushLog(`Quote error: ${e?.message || String(e)}`, 'error');
      enqueueSnackbar(e?.message || 'Quote failed', { variant: 'error' });
    }
  }

  async function doSwap() {
    if (!quote) return; setSending(true);
    try {
      pushLog('Swap: building + sending…');
      const r = await swapExecute({ quoteResponse: quote });
      setSig(r.signature); pushLog(`Swap sent: ${r.signature}`, 'success');
      enqueueSnackbar('Swap sent', { variant: 'success' });
    } catch (e) {
      pushLog(`Swap error: ${e?.message || String(e)}`, 'error');
      enqueueSnackbar(e?.message || 'Swap failed', { variant: 'error' });
    }
    setSending(false);
  }

  return (
    <Stack spacing={2}>
      {/* SWAP FORM (no tabs here; tabs live in JupiterPage wrapper) */}
      <MainCard title="Headless Swap">
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <TextField select fullWidth label="Token In" value={inSym} onChange={(e)=>setInSym(e.target.value)}>
              {TOKENS.map((t) => <MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField select fullWidth label="Token Out" value={outSym} onChange={(e)=>setOutSym(e.target.value)}>
              {TOKENS.map((t) => <MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField fullWidth label="Amount (in)" value={amountUi} onChange={(e)=>setAmountUi(e.target.value)}
              helperText={usdPrice ? `≈ $${(Number(amountUi || 0) * usdPrice).toLocaleString(undefined, { maximumFractionDigits: 2 })}` : ' '} />
          </Grid>
          <Grid item xs={12} md={2}><TextField fullWidth label="Slippage (bps)" value={slip} onChange={(e)=>setSlip(e.target.value)} /></Grid>
          <Grid item xs={12} md={2}><TextField fullWidth label="Profit thresh (bps)" value={thresh} onChange={(e)=>setThresh(Number(e.target.value || 0))} /></Grid>
          <Grid item xs={12}><FormControlLabel control={<Switch checked={restrict} onChange={(e)=>setRestrict(e.target.checked)} />} label="Restrict intermediate tokens" /></Grid>
          <Grid item xs={12}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Button variant="outlined" onClick={doQuote} disabled={overMax}>Quote</Button>
              <Button variant="contained" onClick={doSwap} disabled={!quote || sending || overMax}>
                {sending ? 'Swapping…' : 'Swap'}
              </Button>
              {inSym === 'SOL' && est && <Button variant="text" onClick={setMax}>Max (safe)</Button>}
              {overMax && <Chip color="warning" label="Over safe max — lower amount" />}
            </Stack>
          </Grid>
        </Grid>
        {inSym === 'SOL' && est && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="textSecondary">
              Available to swap (est): <b>{est.safeMaxSol.toFixed(6)} SOL</b> • Rent WSOL: {(est.rentWsolLamports/1e9).toFixed(6)}
              {est.needOutAta ? ` • Rent ${outSym} ATA: ${(est.rentOutAtaLamports/1e9).toFixed(6)}` : ''} • Buffer: {(est.bufferLamports/1e9).toFixed(6)}
            </Typography>
          </Box>
        )}
      </MainCard>

      {/* Three equal cards: Quote | Wallet | Transaction */}
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}><QuoteCard quote={quote} rt={rt && { ...rt, ok: (rt.edgeBps ?? -1) >= thresh }} inSym={inSym} outSym={outSym} /></Grid>
        <Grid item xs={12} md={4}><WalletCard /></Grid>
        <Grid item xs={12} md={4}>
          <TransactionCard
            log={txLog}
            onClear={() => setTxLog([])}
            onCopy={async () => {
              const text = txLog.map((r) => `${r.ts} [${r.level}] ${r.msg}`).join('\n');
              try { await navigator.clipboard.writeText(text); enqueueSnackbar('Transaction log copied', { variant: 'success' }); }
              catch { enqueueSnackbar('Copy failed', { variant: 'error' }); }
            }}
          />
        </Grid>
      </Grid>
    </Stack>
  );
}

/* ------------------------------------------------------------------ */
/* Page wrapper (header with image + tabs lives here)                  */
/* ------------------------------------------------------------------ */
export default function JupiterPage() {
  const [tab, setTab] = useState(2); // land on Swaps by default

  return (
    <Stack spacing={2}>
      {/* Header WITHOUT breadcrumbs + Jupiter image on the left */}
      <MainCard content={false}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', px: 2, pt: 2 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <img
              src="/static/images/jupiter.jpg"   // ensure file exists at /static/images/jupiter.jpg
              alt="Jupiter"
              width={28}
              height={28}
              style={{ objectFit: 'cover', borderRadius: 6 }}
            />
            <Typography variant="h5" fontWeight={700}>Jupiter</Typography>
          </Stack>
          <Chip color="primary" label="Headless" />
        </Box>

        <Divider sx={{ mt: 2 }} />

        {/* Tabs live here so 'tab' is in scope */}
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" sx={{ px: 2 }}>
          <Tab label="Spot Triggers" />
          <Tab label="Perps TP/SL" />
          <Tab label="Swaps" />
        </Tabs>
      </MainCard>

      {/* Tab content */}
      {tab === 0 && <><SpotTriggerForm /><SpotTriggerTable /></>}
      {tab === 1 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}><MarketsPanel /></Grid>
          <Grid item xs={12} md={6}><PositionsPanel /></Grid>
        </Grid>
      )}
      {tab === 2 && (
        <Stack spacing={2}>
          <SendCard onLog={(msg, level='info')=>{
            // optional: you can plumb this into your TransactionCard if you want to share logs
            enqueueSnackbar(msg, { variant: level === 'error' ? 'error' : (level === 'success' ? 'success' : 'info') });
          }}/>
          <SwapsTab />
        </Stack>
      )}
    </Stack>
  );
}
