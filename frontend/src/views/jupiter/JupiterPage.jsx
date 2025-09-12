// src/views/jupiter/JupiterPage.jsx
import { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { enqueueSnackbar } from 'notistack';
import MainCard from 'ui-component/cards/MainCard';
import { createSpotTrigger, listSpotTriggers, cancelSpotTrigger, swapQuote, swapExecute, getUsdPrice } from 'api/jupiter';
import {
  Box, Button, Chip, Divider, Grid, Stack, Tab, Tabs, TextField, Typography, MenuItem, FormControlLabel, Switch
} from '@mui/material';

const TOKENS = [
  { sym: 'SOL', mint: 'So11111111111111111111111111111111111111112', decimals: 9 },
  { sym: 'USDC', mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', decimals: 6 }
];

function SpotTriggerForm() {
  const qc = useQueryClient();
  const [inputSym, setInputSym] = useState('SOL');
  const [outputSym, setOutputSym] = useState('USDC');
  const [amount, setAmount] = useState('0.5');
  const [stop, setStop] = useState('120');
  const [slippageBps, setSlippageBps] = useState(''); // blank => Exact mode
  const [expiry, setExpiry] = useState('');            // seconds from now
  const [sendMode, setSendMode] = useState('execute'); // execute | rpc
  const [rpcUrl, setRpcUrl] = useState('https://api.mainnet-beta.solana.com');

  const sym = (s) => TOKENS.find(t => t.sym === s);

  const preview = useMemo(() => {
    const amountNum = Number(amount || 0);
    const stopNum = Number(stop || 0);
    if (!amountNum || !stopNum) return null;
    const making = Math.floor(amountNum * 10 ** sym(inputSym).decimals);
    const taking = Math.floor(amountNum * stopNum * 10 ** sym(outputSym).decimals);
    return { making, taking };
  }, [amount, stop, inputSym, outputSym]);

  const create = useMutation({
    mutationFn: async () => {
      const payload = {
        inputMint: sym(inputSym).mint,
        outputMint: sym(outputSym).mint,
        amount: Number(amount),
        stopPrice: Number(stop),
        slippageBps: slippageBps !== '' ? Number(slippageBps) : undefined,
        expirySeconds: expiry !== '' ? Number(expiry) : undefined,
        sendMode,
        rpcUrl: sendMode === 'rpc' ? rpcUrl : undefined
      };
      return await createSpotTrigger(payload);
    },
    onSuccess: (res) => {
      enqueueSnackbar('Trigger order created', { variant: 'success' });
      qc.invalidateQueries(['spotTriggers']);
    },
    onError: (err) => enqueueSnackbar(err?.message || 'Failed to create trigger', { variant: 'error' })
  });

  return (
    <MainCard title="New Spot Trigger">
      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Token In" value={inputSym} onChange={(e) => setInputSym(e.target.value)}>
            {TOKENS.map((t) => <MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Token Out" value={outputSym} onChange={(e) => setOutputSym(e.target.value)}>
            {TOKENS.map((t) => <MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
          </TextField>
        </Grid>
        <Grid item xs={12} md={2}>
          <TextField fullWidth label="Amount (in)" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </Grid>
        <Grid item xs={12} md={2}>
          <TextField fullWidth label="Stop Price (per 1 in OUT units)" value={stop} onChange={(e) => setStop(e.target.value)} />
        </Grid>
        <Grid item xs={12} md={2}>
          <TextField fullWidth label="Slippage (bps, Ultra)" value={slippageBps} onChange={(e) => setSlippageBps(e.target.value)} placeholder="blank = Exact" />
        </Grid>
        <Grid item xs={12} md={3}>
          <TextField fullWidth label="Expiry (seconds from now)" value={expiry} onChange={(e) => setExpiry(e.target.value)} placeholder="optional" />
        </Grid>
        <Grid item xs={12} md={3}>
          <TextField select fullWidth label="Send Mode" value={sendMode} onChange={(e) => setSendMode(e.target.value)}>
            <MenuItem value="execute">Execute via Jupiter</MenuItem>
            <MenuItem value="rpc">Send via my RPC</MenuItem>
          </TextField>
        </Grid>
        {sendMode === 'rpc' && (
          <Grid item xs={12} md={6}>
            <TextField fullWidth label="RPC URL" value={rpcUrl} onChange={(e) => setRpcUrl(e.target.value)} />
          </Grid>
        )}
        <Grid item xs={12}>
          <Stack direction="row" spacing={2} alignItems="center">
            {preview && (
              <Typography variant="caption">
                makingAmount: <b>{preview.making.toLocaleString()}</b> • takingAmount: <b>{preview.taking.toLocaleString()}</b>
              </Typography>
            )}
            <Chip size="small" label="Fires when live route meets your stop" />
          </Stack>
        </Grid>
        <Grid item xs={12}>
          <Button variant="contained" onClick={() => create.mutate()} disabled={create.isPending}>
            {create.isPending ? 'Submitting…' : 'Create Trigger'}
          </Button>
        </Grid>
      </Grid>
    </MainCard>
  );
}

function SpotTriggerTable() {
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['spotTriggers'],
    queryFn: () => listSpotTriggers({ status: 'active' })
  });

  const cancel = useMutation({
    mutationFn: (payload) => cancelSpotTrigger(payload),
    onSuccess: () => {
      enqueueSnackbar('Order canceled', { variant: 'success' });
      qc.invalidateQueries(['spotTriggers']);
    },
    onError: (e) => enqueueSnackbar('Failed to cancel', { variant: 'error' })
  });

  return (
    <MainCard title="Active Spot Triggers" secondary={<Button onClick={() => refetch()}>Refresh</Button>}>
      {isLoading ? <Typography>Loading…</Typography> : isError ? <Typography color="error">Failed to load.</Typography> : (
        <Box sx={{ overflowX: 'auto' }}>
          <table className="table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Order</th>
                <th>Pair</th>
                <th>Stop</th>
                <th>Created</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(data?.orders || []).map((o) => (
                <tr key={o.order}>
                  <td><code>{o.order}</code></td>
                  <td>{o.inputMint?.slice(0,4)}… → {o.outputMint?.slice(0,4)}…</td>
                  <td>{o.params?.takingAmount}</td>
                  <td>{o.createdAt ? new Date(o.createdAt * 1000).toLocaleString() : '-'}</td>
                  <td>{o.status}</td>
                  <td><Button size="small" color="error" onClick={() => cancel.mutate({ order: o.order })}>Cancel</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      )}
    </MainCard>
  );
}

function PerpsTabPlaceholder() {
  return (
    <MainCard title="Perps TP / SL">
      <Typography variant="body2">
        We will attach/review Perps triggers here (via Anchor IDL). Coming soon.
      </Typography>
    </MainCard>
  );
}

function SwapsTab() {
  const TOKENS = [
    { sym:'SOL',  mint:'So11111111111111111111111111111111111111112', dec:9 },
    { sym:'USDC', mint:'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', dec:6 },
    { sym:'mSOL', mint:'mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So', dec:9 },
    { sym:'JitoSOL', mint:'J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn', dec:9 }
  ];
  const [inSym,setInSym]=useState('SOL');
  const [outSym,setOutSym]=useState('USDC');
  const [amountUi,setAmountUi]=useState('0.1');
  const [slip,setSlip]=useState('50');
  const [mode,setMode]=useState('ExactIn');
  const [restrict,setRestrict]=useState(true);
  const [quote,setQuote]=useState(null);
  const [sig,setSig]=useState('');
  const [sending,setSending]=useState(false);

  // NEW: live USD price & computed USD amount
  const [usdPrice, setUsdPrice] = useState(null);
  const sym=(s)=>TOKENS.find(t=>t.sym===s);

  // fetch USD price whenever Token In changes (debounced)
  useEffect(() => {
    let alive = true;
    const t = setTimeout(async () => {
      try {
        const r = await getUsdPrice(sym(inSym).mint, 'USDC');
        if (alive) setUsdPrice(Number(r.price));
      } catch {
        if (alive) setUsdPrice(null);
      }
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [inSym]);

  const amountUsd = (() => {
    const a = Number(amountUi || 0);
    return usdPrice ? a * usdPrice : null;
  })();

  async function doQuote() {
    setSig('');
    setQuote(null);
    const amt = Math.floor(Number(amountUi) * 10 ** sym(inSym).dec);
    const q = await swapQuote({
      inputMint: sym(inSym).mint,
      outputMint: sym(outSym).mint,
      amount: amt,
      slippageBps: Number(slip||50),
      swapMode: mode,
      restrictIntermediates: restrict
    });
    setQuote(q);
  }
  async function doSwap() {
    if(!quote) return;
    setSending(true);
    try {
      const r = await swapExecute({ quoteResponse: quote });
      setSig(r.signature);
    } catch(e) { enqueueSnackbar(e.message || 'Swap failed',{variant:'error'}); }
    setSending(false);
  }

  return (
    <Stack spacing={2}>
      <MainCard title="Headless Swap">
        <Grid container spacing={2}>
          <Grid item xs={12} md={3}>
            <TextField select fullWidth label="Token In" value={inSym} onChange={e=>setInSym(e.target.value)}>
              {TOKENS.map(t=><MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} md={3}>
            <TextField select fullWidth label="Token Out" value={outSym} onChange={e=>setOutSym(e.target.value)}>
              {TOKENS.map(t=><MenuItem key={t.sym} value={t.sym}>{t.sym}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              label="Amount (in)"
              value={amountUi}
              onChange={e=>setAmountUi(e.target.value)}
              // NEW: show USD equiv directly under the input
              helperText={
                amountUsd !== null
                  ? `≈ $${amountUsd.toLocaleString(undefined,{maximumFractionDigits: 2})}`
                  : ' '
              }
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField fullWidth label="Slippage (bps)" value={slip} onChange={e=>setSlip(e.target.value)} />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField select fullWidth label="Mode" value={mode} onChange={e=>setMode(e.target.value)}>
              <MenuItem value="ExactIn">ExactIn</MenuItem>
              <MenuItem value="ExactOut">ExactOut</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={12}>
            <FormControlLabel control={<Switch checked={restrict} onChange={e=>setRestrict(e.target.checked)} />} label="Restrict intermediate tokens" />
          </Grid>
          <Grid item xs={12}>
            <Stack direction="row" spacing={1}>
              <Button variant="outlined" onClick={doQuote}>Quote</Button>
              <Button variant="contained" disabled={!quote || sending} onClick={doSwap}>
                {sending ? 'Swapping…' : 'Swap'}
              </Button>
            </Stack>
          </Grid>
        </Grid>
      </MainCard>

      {quote && (
        <MainCard title="Quote">
          <Typography variant="body2">outAmount (atoms): <b>{quote.outAmount}</b></Typography>
          <Typography variant="body2">otherAmountThreshold: <b>{quote.otherAmountThreshold}</b></Typography>
          <Typography variant="body2">priceImpactPct: <b>{quote.priceImpactPct}</b></Typography>
        </MainCard>
      )}

      {sig && (
        <MainCard title="Broadcast">
          <Typography variant="body2">Signature: <code>{sig}</code></Typography>
        </MainCard>
      )}
    </Stack>
  );
}

export default function JupiterPage() {
  const [tab, setTab] = useState(0);
  return (
    <Stack spacing={2}>
      <MainCard title="Jupiter" secondary={<Chip color="primary" label="Headless" />}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable">
          <Tab label="Spot Triggers" />
          <Tab label="Perps TP/SL" />
          <Tab label="Swaps" />
        </Tabs>
      </MainCard>

      {tab === 0 && (
        <Stack spacing={2}>
          <SpotTriggerForm />
          <SpotTriggerTable />
        </Stack>
      )}
      {tab === 1 && <PerpsTabPlaceholder />}
      {tab === 2 && <SwapsTab />}
    </Stack>
  );
}
