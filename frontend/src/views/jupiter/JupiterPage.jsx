// frontend/src/views/jupiter/JupiterPage.jsx
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useSnackbar } from 'notistack';

import {
  Box,
  Button,
  Chip,
  Divider,
  Grid,
  IconButton,
  MenuItem,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
  FormControlLabel
} from '@mui/material';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

import MainCard from 'ui-component/cards/MainCard';
import MarketsPanel from 'components/jupiter/Perps/MarketsPanel.jsx';
import PositionsPanel from 'components/jupiter/Perps/PositionsPanel.jsx';
import OrderForm from 'components/jupiter/Perps/OrderForm.jsx';
import {
  whoami,
  signerInfo,
  walletPortfolio,
  estimateSolSpend,
  swapQuote,
  swapExecute,
  getUsdPrice,
  txlogLatest,
  txlogList,
  sendToken
} from 'api/jupiter';

/* ------------------------------------------------------------------ */
/* Tokens                                                              */
/* ------------------------------------------------------------------ */
const TOKENS = [
  { sym: 'SOL',     mint: 'So11111111111111111111111111111111111111112', decimals: 9 },
  { sym: 'USDC',    mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', decimals: 6 },
  { sym: 'mSOL',    mint: 'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So',  decimals: 9 },
  { sym: 'JitoSOL', mint: 'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', decimals: 9 }
];
const tokenBySym = (s) => TOKENS.find(t => t.sym === s) || TOKENS[0];

/* helpers */
const atomsToUi = (atoms, decimals) => Number(atoms || 0) / 10 ** Number(decimals || 0);
const fmt       = (n, dp = 6) => Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: dp });
const pct       = (x) => (Number(x || 0) * 100).toLocaleString(undefined, { maximumFractionDigits: 4 }) + '%';

/* ------------------------------------------------------------------ */
/* Base58 sanitation (prevents -32602 from RPC)                        */
/* ------------------------------------------------------------------ */
const BASE58_ALPH = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
const BASE58_RE   = /^[1-9A-HJ-NP-Za-km-z]+$/;
const BASE58_FIND = /[1-9A-HJ-NP-Za-km-z]{32,}/g;

const extractPubkey = (s) => {
  if (!s) return '';
  s = String(s).trim();
  const low = s.toLowerCase();
  if (low.startsWith('solana:')) return s.split(':', 1)[1].split('?', 1)[0];
  const m = s.match(/address\/([1-9A-HJ-NP-Za-km-z]+)/i);
  if (m && m[1]) return m[1];
  const s0 = s.split(/[?#\s]/)[0];
  if (BASE58_RE.test(s0)) return s0;
  const hits = s.match(BASE58_FIND);
  if (hits && hits.length) { hits.sort((a,b)=>b.length-a.length); return hits[0]; }
  return s0;
};
// sanitize to base58 only, after extracting pubkey from URI/explorer URL
const sanitizeBase58 = (s) => extractPubkey(s).replace(/[^1-9A-HJ-NP-Za-km-z]/g, '');

/* ------------------------------------------------------------------ */
/* Send Tokens                                                         */
/* ------------------------------------------------------------------ */
function SendCard() {
  const { enqueueSnackbar } = useSnackbar();
  const [mintSym, setMintSym]   = useState('USDC');
  const [to, setTo]             = useState('');
  const [amountUi, setAmountUi] = useState('');
  const [sending, setSending]   = useState(false);
  const [usd, setUsd]           = useState(null);
  const [cleanNote, setCleanNote] = useState('');

  const tok = tokenBySym(mintSym);

  // price
  useEffect(() => {
    let live = true;
    (async () => {
      try { const r = await getUsdPrice(tok.mint, 'USDC'); if (live) setUsd(Number(r.price)); }
      catch { if (live) setUsd(null); }
    })();
    return () => { live = false; };
  }, [mintSym]);

  const amountUsd = useMemo(() => {
    const ui = Number(amountUi || 0);
    if (usd == null || !ui || !Number.isFinite(ui)) return null;
    return ui * usd;
  }, [amountUi, usd]);

  // block non-base58 keystrokes
  const onBeforeInput = (e) => {
    const d = e.nativeEvent?.data;
    if (!d || d.length !== 1) return;
    if (!BASE58_ALPH.includes(d)) {
      e.preventDefault();
      setCleanNote(`Removed non-base58 character '${d}'.`);
    }
  };
  // sanitize on change/paste
  const onChangeRecipient = (e) => {
    const before = e.target.value;
    const after  = sanitizeBase58(before);
    setTo(after);
    setCleanNote(after !== before ? 'Removed non-base58 characters.' : '');
  };
  const onPasteRecipient = (e) => {
    try {
      const text = (e.clipboardData || window.clipboardData).getData('text');
      const clean = sanitizeBase58(text);
      setTo(clean);
      setCleanNote(clean !== text ? 'Removed non-base58 characters from pasted value.' : '');
      e.preventDefault();
    } catch {}
  };

  const toNorm  = sanitizeBase58(to);
  const invalid = !toNorm || !BASE58_RE.test(toNorm);

  const onSend = async () => {
    try {
      setSending(true);
      if (invalid) { enqueueSnackbar('Enter a valid base58 address', { variant: 'warning' }); return; }
      const ui = Number(amountUi || 0);
      if (!ui || ui <= 0) { enqueueSnackbar('Enter a positive amount', { variant: 'warning' }); return; }
      const atoms = Math.floor(ui * 10 ** tok.decimals);
      if (!atoms) { enqueueSnackbar('Amount too small for this token', { variant: 'warning' }); return; }

      const r = await sendToken({ mint: tok.mint, to: toNorm, amountAtoms: atoms });
      enqueueSnackbar('Send submitted', { variant: 'success' });
      console.log('[SEND] signature:', r.signature);
    } catch (e) {
      enqueueSnackbar(e?.message || String(e), { variant: 'error' });
    } finally { setSending(false); }
  };

  return (
    <MainCard title="Send Tokens">
      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Token" value={mintSym} onChange={(e)=>setMintSym(e.target.value)}>
            {TOKENS.map((x)=> <MenuItem key={x.sym} value={x.sym}>{x.sym}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} md={5}>
          <TextField
            fullWidth label="Recipient (pubkey)" value={to}
            onBeforeInput={onBeforeInput}
            onChange={onChangeRecipient}
            onPaste={onPasteRecipient}
            error={!!to && invalid}
            helperText={invalid ? (cleanNote || 'Enter a valid base58 address (no 0/O/I/l or punctuation)') : (cleanNote || ' ')}
            inputProps={{ spellCheck:false, autoCapitalize:'off', autoCorrect:'off' }}
          />
        </Grid>
        <Grid item xs={12} md={2}>
          <TextField fullWidth label="Amount" value={amountUi} onChange={(e)=>setAmountUi(e.target.value)}
            helperText={amountUsd != null ? `≈ $${amountUsd.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : ' '} />
        </Grid>
        <Grid item xs={12} md={2}>
          <Button fullWidth variant="contained" onClick={onSend} disabled={sending || invalid || !amountUi}>
            {sending ? 'Sending…' : 'Send'}
          </Button>
        </Grid>
      </Grid>
      <Typography variant="caption" color="textSecondary">If the recipient doesn’t have an ATA, we’ll create it automatically (uses a small amount of SOL).</Typography>
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Wallet card (simple; hook a richer version if you want)             */
/* ------------------------------------------------------------------ */
function WalletCard() {
  const qc = useQueryClient();
  const who  = useQuery({ queryKey:['who'],       queryFn: whoami,     staleTime:5000, retry:0 });
  const sinf = useQuery({ queryKey:['signerInfo'], queryFn: signerInfo, staleTime:10000, retry:0 });

  const mints = TOKENS.map(t=>t.mint);
  const port  = useQuery({
    queryKey:['portfolio', mints.join(',')],
    queryFn: ()=> walletPortfolio(mints),
    enabled: !!who.data, staleTime:5000, retry:0
  });

  const short = (s)=> s ? `${s.slice(0,4)}…${s.slice(-4)}` : '';
  const pub   = who.data?.pubkey || sinf.data?.pubkey;

  return (
    <MainCard title="Wallet" secondary={<Button size="small" onClick={()=>{
      qc.invalidateQueries({ queryKey:['who'] });
      qc.invalidateQueries({ queryKey:['signerInfo'] });
      qc.invalidateQueries({ queryKey:['portfolio'] });
    }}>Refresh</Button>}>
      {!who.data ? <Typography>Loading…</Typography>
        : port.isError ? <Typography color="error">{port.error?.message || 'Portfolio error'}</Typography>
        : port.isLoading ? <Typography>Loading balances…</Typography>
        : (
          <Stack spacing={1}>
            <Typography variant="body2">Pubkey: <code>{short(pub)}</code></Typography>
            {(port.data?.items || []).map((it)=>(
              <Typography key={it.mint} variant="body2">
                {it.sym}: <b>{fmt(it.amount)}</b> ({it.usd != null ? `$${Number(it.usd).toFixed(2)}` : '—'})
              </Typography>
            ))}
          </Stack>
        )}
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Quote + round-trip card (condensed)                                 */
/* ------------------------------------------------------------------ */
function QuoteCard({ quote, rt, inSym, outSym }) {
  const inDec  = tokenBySym(inSym).decimals;
  const outDec = tokenBySym(outSym).decimals;

  const pill = (() => {
    if (!rt) return { text: 'no edge', color: 'default', tip: 'No round-trip yet.' };
    const e = rt.edgeBps ?? 0;
    const tip = 'Round-trip edge; positive = profit';
    if (e >= 50) return { text: `profit +${e.toFixed(2)} bps`, color: 'success', tip };
    if (e >= 0)  return { text: `near +${e.toFixed(2)} bps`,   color: 'warning', tip };
    return { text: `${e.toFixed(2)} bps`, color: 'error', tip };
  })();

  return (
    <MainCard title="Quote" secondary={<Tooltip title={pill.tip}><Chip color={pill.color} label={pill.text}/></Tooltip>}>
      {quote ? (
        <Stack spacing={0.75}>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <Typography variant="body2">
              outAmount (atoms): <b>{quote.outAmount}</b>{' '}
              <span style={{opacity:.8}}>({fmt(atomsToUi(quote.outAmount, outDec))} {outSym})</span>
            </Typography>
            <Tooltip title="Estimated output at quote time.">
              <IconButton size="small"><InfoOutlinedIcon fontSize="inherit" /></IconButton>
            </Tooltip>
          </Stack>
          <Typography variant="body2">
            otherAmountThreshold: <b>{quote.otherAmountThreshold}</b>{' '}
            <span style={{opacity:.8}}>({fmt(atomsToUi(quote.otherAmountThreshold, outDec))} {outSym})</span>
          </Typography>
          <Typography variant="body2">priceImpactPct: <b>{pct(quote.priceImpactPct)}</b></Typography>

          {rt && (
            <>
              <Divider sx={{ my:1 }}/>
              <Typography variant="subtitle2">Round-trip</Typography>
              <Typography variant="body2">A→B minOut (B): <b>{rt.a2bMinOut}</b>{' '}
                <span style={{opacity:.8}}>({fmt(atomsToUi(rt.a2bMinOut, outDec))} {outSym})</span>
              </Typography>
              <Typography variant="body2">B→A minOut (A): <b>{rt.b2aMinOut}</b>{' '}
                <span style={{opacity:.8}}>({fmt(atomsToUi(rt.b2aMinOut, inDec))} {inSym})</span>
              </Typography>
              <Typography variant="body2">Edge: <b>{(rt.edgeTokens ?? 0).toLocaleString()}</b> atoms of {inSym}</Typography>
            </>
          )}
        </Stack>
      ) : <Typography variant="body2" color="textSecondary">No quote yet.</Typography>}
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Transaction card (simple placeholders)                              */
/* ------------------------------------------------------------------ */
function TransactionCard() {
  const latest  = useQuery({ queryKey: ['txlogLatest'], queryFn: txlogLatest, staleTime: 0, retry: 0 });
  const history = useQuery({ queryKey: ['txlogList'],   queryFn: () => txlogList(25), staleTime: 0, retry: 0 });

  return (
    <MainCard title="Transaction">
      {latest.isSuccess && (
        <>
          <Typography variant="body2"><b>Signature:</b> {latest.data.signature || latest.data.execution?.sig}</Typography>
          <Divider sx={{ my:1 }}/>
        </>
      )}
      {history.isSuccess && (
        <Box sx={{ maxHeight: 240, overflowY:'auto', fontFamily:'ui-monospace, Menlo, Consolas, monospace', fontSize:12 }}>
          <table style={{ width:'100%' }}>
            <thead><tr><th align="left">Time</th><th align="left">Pair</th><th align="right">Proj bps</th><th align="right">Act bps</th><th align="right">Act USD</th><th align="left">Sig</th></tr></thead>
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
                    <td align="right">{acb != null ? prb.toFixed(2) : '—'}</td>
                    <td align="right">{usd != null ? Number(usd).toFixed(3) : '—'}</td>
                    <td>{(e.execution?.sig || '').slice(0,6)}…</td>
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
/* Headless Swap (condensed)                                           */
/* ------------------------------------------------------------------ */
function SwapsTab() {
  const { enqueueSnackbar } = useSnackbar();
  const [inSym, setInSym]       = useState('SOL');
  const [outSym, setOutSym]     = useState('USDC');
  const [amountUi, setAmountUi] = useState('0.1');
  const [slip, setSlip]         = useState('50');
  const [restrict, setRestrict] = useState(true);

  const [quote, setQuote] = useState(null);
  const [rt, setRt]       = useState(null);
  const [sending, setSending] = useState(false);

  const [usdPrice, setUsdPrice] = useState(null);
  useEffect(() => {
    let live=true;
    (async()=>{ try{ const r=await getUsdPrice(tokenBySym(inSym).mint,'USDC'); if(live) setUsdPrice(Number(r.price)); } catch{ if(live) setUsdPrice(null); } })();
    return ()=>{live=false};
  }, [inSym]);
  const amountUsd = usdPrice ? Number(amountUi || 0) * usdPrice : null;

  const push = (m, v='info') => enqueueSnackbar(m, { variant:v });

  async function computeRT(q, amtAtoms) {
    try{
      const bMin = Number(q.otherAmountThreshold);
      const back = await swapQuote({
        inputMint: tokenBySym(outSym).mint,
        outputMint: tokenBySym(inSym).mint,
        amount: bMin, slippageBps: Number(slip || 50),
        swapMode: 'ExactIn', restrictIntermediates: restrict
      });
      const aBack = Number(back.otherAmountThreshold);
      const edgeTokens = aBack - Number(amtAtoms);
      const edgeBps = (edgeTokens / Number(amtAtoms)) * 10_000;
      setRt({ a2bMinOut: bMin, b2aMinOut: aBack, edgeTokens, edgeBps });
    } catch(e) { setRt(null); push(e?.message || 'RT failed', 'error'); }
  }

  async function doQuote() {
    try{
      setQuote(null); setRt(null); setSending(false);
      const amtAtoms = Math.floor(Number(amountUi || 0) * 10 ** tokenBySym(inSym).decimals);
      const q = await swapQuote({
        inputMint: tokenBySym(inSym).mint,
        outputMint: tokenBySym(outSym).mint,
        amount: amtAtoms, slippageBps: Number(slip || 50),
        swapMode: 'ExactIn', restrictIntermediates: restrict
      });
      setQuote(q); await computeRT(q, amtAtoms);
    } catch(e) { push(e?.message || 'Quote failed', 'error'); }
  }

  async function doSwap() {
    if (!quote) return;
    setSending(true);
    try{
      const r = await swapExecute({ quoteResponse: quote });
      push(`Swap sent: ${r.signature}`, 'success');
    } catch(e) { push(e?.message || 'Swap failed', 'error'); }
    setSending(false);
  }

  return (
    <MainCard title="Headless Swap">
      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Token In" value={inSym} onChange={(e)=>setInSym(e.target.value)}>
            {TOKENS.map(t => <MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Token Out" value={outSym} onChange={(e)=>setOutSym(e.target.value)}>
            {TOKENS.map(t => <MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} md={2}>
          <TextField fullWidth label="Amount (in)" value={amountUi} onChange={(e)=>setAmountUi(e.target.value)}
            helperText={amountUsd ? `≈ $${amountUsd.toLocaleString(undefined,{maximumFractionDigits:2})}` : ' '} />
        </Grid>
        <Grid item xs={12} md={2}><TextField fullWidth label="Slippage (bps)" value={slip} onChange={(e)=>setSlip(e.target.value)} /></Grid>
        <Grid item xs={12} md={2}>
          <FormControlLabel control={<Switch checked={restrict} onChange={(e)=>setRestrict(e.target.checked)} />} label="Restrict intermediate tokens" />
        </Grid>
        <Grid item xs={12}>
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={doQuote}>Quote</Button>
            <Button variant="contained" onClick={doSwap} disabled={!quote || sending}>
              {sending ? 'Swapping…' : 'Swap'}
            </Button>
          </Stack>
        </Grid>
      </Grid>
    </MainCard>
  );
}

/* ------------------------------------------------------------------ */
/* Page wrapper                                                        */
/* ------------------------------------------------------------------ */
export default function JupiterPage() {
  const [tab, setTab] = useState(2); // default to Swaps

  return (
    <Stack spacing={2}>
      <MainCard content={false}>
        <Box sx={{ display:'flex', alignItems:'center', justifyContent:'space-between', px:2, pt:2 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <img src="/static/images/jupiter.jpg" alt="Jupiter" width={28} height={28} style={{ objectFit:'cover', borderRadius:6 }} />
            <Typography variant="h5" fontWeight={700}>Jupiter</Typography>
          </Stack>
          <Chip color="primary" label="Headless" />
        </Box>
        <Divider sx={{ mt:2 }}/>
        <Tabs value={tab} onChange={(_,v)=>setTab(v)} variant="scrollable" sx={{ px:2 }}>
          <Tab label="Spot Triggers" />
          <Tab label="Perps TP/SL" />
          <Tab label="Swaps" />
        </Tabs>
      </MainCard>

      {tab === 0 && <MainCard><Typography>Spot Triggers coming soon…</Typography></MainCard>}
      {tab === 1 && (
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <MarketsPanel />
            </Grid>
            <Grid item xs={12} md={6}>
              <PositionsPanel />
            </Grid>
          </Grid>
          <OrderForm />
        </Stack>
      )}

      {tab === 2 && (
        <Stack spacing={2}>
          <SendCard />
          <SwapsTab />
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}><WalletCard /></Grid>
            <Grid item xs={12} md={6}><TransactionCard /></Grid>
          </Grid>
        </Stack>
      )}
    </Stack>
  );
}
