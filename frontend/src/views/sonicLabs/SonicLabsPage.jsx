import MainCard from 'ui-component/cards/MainCard';
import {
  Typography, Button, Stack, Card, CardContent, CardActions, Chip, Divider, Box,
  ToggleButtonGroup, ToggleButton, TextField
} from '@mui/material';
import { useMemo, useRef, useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? '/api' : '');
const DEDICATED_ALIAS = 'Sonic - Auto';
const JUP_PERPS_URL = 'https://jup.ag/perps';

/* helpers */
async function api(method, path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const text = await res.text();
  let data;
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
  if (!res.ok || data?.ok === false) {
    const msg = data?.detail || data?.error || text || res.statusText;
    throw new Error(`${res.status} ${msg}`);
  }
  return data;
}
const apiPost = (p, b) => api('POST', p, b);
const apiGet  = (p)    => api('GET',  p);

/* steps */
function useStepLibrary(log, asset) {
  const steps = useMemo(() => ([
    {
      id: 'open',
      title: 'Open dedicated browser',
      desc: `Launch Chrome with profile "${DEDICATED_ALIAS}" and open Jupiter.`,
      run: async () => {
        await apiPost('/auto-core/open-browser', { wallet_id: DEDICATED_ALIAS, url: JUP_PERPS_URL });
        log('launched persistent context; connecting…');
        await apiPost('/auto-core/connect-jupiter', { url: JUP_PERPS_URL });
        return { ok: true };
      }
    },
    {
      id: 'connect',
      title: 'Connect Solflare',
      desc: 'Open Connect → pick Solflare. Unlock/Approve if prompted.',
      run: async () => {
        const r = await apiPost('/auto-core/connect-jupiter', { url: JUP_PERPS_URL });
        log(r.detail || JSON.stringify(r));
        return r;
      }
    },
    {
      id: 'select-asset',
      title: `Select Asset (${asset})`,
      desc: 'Click the asset chip in Perps (SOL / ETH / WBTC).',
      run: async () => {
        const r = await apiPost('/auto-core/select-asset', { symbol: asset });
        log(`select-asset rc=${r.rc} ok=${r.ok}`);
        if (!r.ok) throw new Error(`select asset failed (code ${r.rc})`);
        return r;
      }
    },
    {
      id: 'status',
      title: 'Show session status',
      desc: 'Fetch tracked Playwright sessions (pid, started_at).',
      run: async () => {
        const r = await apiGet('/auto-core/jupiter-status');
        log(JSON.stringify(r, null, 2));
        return r;
      }
    },
    {
      id: 'close',
      title: 'Close browser',
      desc: `Close Chrome for "${DEDICATED_ALIAS}" if running.`,
      run: async () => {
        const r = await apiPost('/auto-core/close-browser', {});
        log(JSON.stringify(r));
        return r;
      }
    },
  ]), [log, asset]);

  const byId = useMemo(() => Object.fromEntries(steps.map(s => [s.id, s])), [steps]);
  return { steps, byId };
}

/* UI bits */
function StepCard({ step, onRun, onAdd, disabled }) {
  return (
    <Card variant="outlined" sx={{ minWidth: 280, flex: 1 }}>
      <CardContent>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>{step.title}</Typography>
        <Typography variant="body2" color="text.secondary">{step.desc}</Typography>
      </CardContent>
      <CardActions sx={{ justifyContent: 'space-between', px: 2, pb: 2 }}>
        <Button size="small" variant="contained" onClick={() => onRun(step)} disabled={disabled}>Run</Button>
        <Button size="small" onClick={() => onAdd(step)} disabled={disabled}>Add to Workflow</Button>
      </CardActions>
    </Card>
  );
}
function LogConsole({ lines }) {
  const ref = useRef(null);
  if (ref.current) setTimeout(() => { ref.current.scrollTop = ref.current.scrollHeight; }, 0);
  return (
    <Box sx={{
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
      bgcolor: 'background.default',
      border: '1px solid rgba(255,255,255,0.12)',
      borderRadius: 1,
      p: 1.5, height: 220, overflow: 'auto'
    }} ref={ref}>
      {lines.length ? lines.map((l, i) => <div key={i}>{l}</div>)
                     : <Typography variant="body2" color="text.secondary">Logs will appear here…</Typography>}
    </Box>
  );
}

/* page */
export default function SonicLabsPage() {
  const [busy, setBusy] = useState(false);
  const [logs, setLogs] = useState([]);
  const [workflow, setWorkflow] = useState(['open', 'select-asset']);
  const [asset, setAsset] = useState('SOL');
  const [status, setStatus] = useState('');
  const [walletId, setWalletId] = useState('default');
  const [addr, setAddr] = useState('V8iveiirFvX7m7psPHWBJW85xPk1ZB6U4Ep9GUV2THW');
  const [bal, setBal] = useState(null);
  const [loadingBal, setLoadingBal] = useState(false);
  const [loadingAddr, setLoadingAddr] = useState(false);

  const log = (msg) => setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  const { steps, byId } = useStepLibrary(log, asset);

  const addToWorkflow = (step) => setWorkflow((prev) => [...prev, step.id]);
  const clearWorkflow = () => setWorkflow([]);
  const removeFromWorkflow = (index) => setWorkflow((prev) => prev.filter((_, i) => i !== index));

  const openJupiter = async () => {
    try {
      setStatus('Opening Jupiter…');
      await apiPost('/auto-core/open-browser', { wallet_id: walletId, url: JUP_PERPS_URL });
      await apiPost('/auto-core/connect-jupiter', { url: JUP_PERPS_URL });
      setStatus(`✅ Opened & (attempted) Connect for "${walletId}"`);
    } catch (e) {
      console.error(e);
      setStatus('❌ Failed to open/connect');
    }
  };
  const closeBrowser = async () => {
    try { await apiPost('/auto-core/close-browser', {}); setStatus('✅ Browser closed'); }
    catch (e) { console.error(e); setStatus('❌ Failed to close browser'); }
  };

  const checkBalance = async () => {
    if (!addr) return;
    setLoadingBal(true);
    try {
      const res = await fetch(`${API_BASE}/solana/balance`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr })
      });
      const data = await res.json();
      if (res.ok) { setBal(data); setStatus('✅ Balance loaded'); }
      else setStatus(`❌ ${data.detail?.message || data.detail || 'Failed to check balance'}`);
    } catch (e) { console.error(e); setStatus('❌ Failed to check balance'); }
    finally { setLoadingBal(false); }
  };

  // auto-fill address from wallet ID mapping
  useEffect(() => {
    const wid = (walletId || '').trim();
    if (!wid) return;
    setLoadingAddr(true);
    fetch(`${API_BASE}/auto-core/wallet-address?wallet_id=${encodeURIComponent(wid)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (data?.address) { setAddr(data.address); setStatus(`✅ Loaded address for "${wid}"`); } })
      .catch(() => {})
      .finally(() => setLoadingAddr(false));
  }, [walletId]);

  const runStep = async (step) => {
    setBusy(true);
    try { log(`▶︎ ${step.title}`); await step.run(); log(`✔ ${step.id} done`); }
    catch (e) { console.error(e); log(`✖ ${step.id} failed: ${e.message || e}`); }
    finally { setBusy(false); }
  };
  const runWorkflow = async () => {
    for (const id of workflow) await runStep(byId[id]);
  };

  return (
    <MainCard title="Sonic Labs">
      <Stack spacing={2}>
        {status && <Typography variant="body2">{status}</Typography>}

        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <TextField
            label="Wallet ID"
            size="small"
            value={walletId}
            onChange={(e) => setWalletId(e.target.value)}
            helperText={loadingAddr ? 'Loading address…' : 'Choose a wallet alias (e.g., Sonic - Leia)'}
          />
        </Stack>
        <Stack direction="row" spacing={2}>
          <Button variant="contained" color="primary" onClick={openJupiter}>Open Jupiter & Connect</Button>
          <Button variant="outlined" color="secondary" onClick={closeBrowser}>Close Browser</Button>
        </Stack>

        <Divider sx={{ my: 3 }} />
        <Typography variant="h6" sx={{ mb: 1 }}>Check On-Chain Balance</Typography>
        <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
          <TextField label="Solana Address" size="small" fullWidth value={addr} onChange={(e) => setAddr(e.target.value.trim())} />
          <Button variant="outlined" onClick={async () => {
            if (!walletId || !addr) return setStatus('❌ Wallet ID and address required');
            try {
              const res = await fetch(`${API_BASE}/auto-core/register-wallet-address`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ wallet_id: walletId, address: addr })
              });
              const data = await res.json();
              if (res.ok) setStatus(`✅ Saved mapping for "${walletId}"`);
              else setStatus(`❌ ${data.detail?.message || data.detail || 'Failed to save'}`);
            } catch (e) { console.error(e); setStatus('❌ Failed to save wallet address'); }
          }}>Save Wallet Address</Button>
          <Button variant="contained" onClick={checkBalance} disabled={loadingBal || !addr}>
            {loadingBal ? 'Checking…' : 'Check Balance'}
          </Button>
        </Stack>
        {bal && <Card variant="outlined"><CardContent><pre style={{ margin: 0 }}>{JSON.stringify(bal, null, 2)}</pre></CardContent></Card>}

        <Divider sx={{ my: 3 }} />
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="body2">Profile</Typography>
          <Chip label={DEDICATED_ALIAS} size="small" />
          <Box sx={{ flexGrow: 1 }} />
          <Typography variant="body2" sx={{ ml: 1 }}>Asset:</Typography>
          <ToggleButtonGroup value={asset} exclusive size="small" onChange={(_, v) => v && setAsset(v)}>
            <ToggleButton value="SOL">SOL</ToggleButton>
            <ToggleButton value="ETH">ETH</ToggleButton>
            <ToggleButton value="WBTC">WBTC</ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        <Typography variant="h6">Step Library</Typography>
        <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap' }}>
          {steps.map((s) => (
            <StepCard key={s.id} step={s} onRun={runStep} onAdd={(st)=>setWorkflow((w)=>[...w, st.id])} disabled={busy} />
          ))}
        </Stack>

        <Divider />
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="h6" sx={{ flexGrow: 1 }}>Workflow</Typography>
          <Button size="small" onClick={runWorkflow} disabled={busy || workflow.length === 0}>Run</Button>
          <Button size="small" onClick={clearWorkflow} disabled={busy || workflow.length === 0}>Clear</Button>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          {workflow.map((id, idx) => (
            <Chip key={`${id}-${idx}`} label={(steps.find(s=>s.id===id)||{title:id}).title}
                  onDelete={() => setWorkflow((w)=>w.filter((_,i)=>i!==idx))}/>
          ))}
        </Stack>

        <LogConsole lines={logs} />
      </Stack>
    </MainCard>
  );
}
