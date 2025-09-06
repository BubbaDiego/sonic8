import MainCard from 'ui-component/cards/MainCard';
import { Typography, Button, Stack, Card, CardContent, CardActions, Chip, Divider, Box, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { useMemo, useRef, useState } from 'react';

// Backend base (works in dev and prod)
const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? '/api' : '');
// Dedicated automation profile
const DEDICATED_ALIAS = 'Sonic - Auto';

/* ---------------- helpers ---------------- */

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

/* ---------------- step library ---------------- */

function useStepLibrary(log, asset) {
  // Each step is a small, testable unit that only talks to the backend.
  const steps = useMemo(() => ([
    {
      id: 'open',
      title: 'Open dedicated browser',
      desc: `Launch Chrome with profile "${DEDICATED_ALIAS}" and open Jupiter.`,
      run: async () => {
        const r = await apiPost('/jupiter/open', { walletId: DEDICATED_ALIAS });
        log(`launched pid=${r.pid} alias=${r.launched}`);
        return r;
      }
    },
    {
      id: 'connect',
      title: 'Connect Solflare',
      desc: 'Click Connect → Solflare (Recently Used). Unlock if prompted.',
      run: async () => {
        const r = await apiPost('/jupiter/connect', {});
        log(r.detail || JSON.stringify(r));
        if (!r.ok) throw new Error(`connect failed (code ${r.code})`);
        return r;
      }
    },
    {
      id: 'select-asset',
      title: 'Select Asset',
      desc: 'Click the asset chip in Perps (SOL / ETH / WBTC).',
      run: async () => {
        const r = await apiPost('/jupiter/select-asset', { symbol: asset });
        log(r.detail || JSON.stringify(r));
        if (!r.ok) throw new Error(`select asset failed (code ${r.code})`);
        return r;
      }
    },
    {
      id: 'status',
      title: 'Show session status',
      desc: 'Fetch tracked Playwright sessions (pid, started_at).',
      run: async () => {
        const r = await apiGet('/jupiter/status');
        log(JSON.stringify(r, null, 2));
        return r;
      }
    },
    {
      id: 'close',
      title: 'Close browser',
      desc: `Close Chrome for "${DEDICATED_ALIAS}" if running.`,
      run: async () => {
        const r = await apiPost('/jupiter/close', { walletId: DEDICATED_ALIAS });
        log(JSON.stringify(r));
        return r;
      }
    },
  ]), [log, asset]);

  const byId = useMemo(() => Object.fromEntries(steps.map(s => [s.id, s])), [steps]);
  return { steps, byId };
}

/* ---------------- UI components ---------------- */

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
  if (ref.current) {
    setTimeout(() => { ref.current.scrollTop = ref.current.scrollHeight; }, 0);
  }
  return (
    <Box sx={{
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
      bgcolor: 'background.default',
      border: '1px solid rgba(255,255,255,0.12)',
      borderRadius: 1,
      p: 1.5,
      height: 220,
      overflow: 'auto'
    }} ref={ref}>
      {lines.length === 0 ? (
        <Typography variant="body2" color="text.secondary">Logs will appear here…</Typography>
      ) : (
        lines.map((l, i) => <div key={i}>{l}</div>)
      )}
    </Box>
  );
}

/* ---------------- main page ---------------- */

export default function SonicLabsPage() {
  const [busy, setBusy] = useState(false);
  const [logs, setLogs] = useState([]);
  const [workflow, setWorkflow] = useState(['open', 'connect', 'select-asset']);
  const [asset, setAsset] = useState('SOL');

  const log = (msg) => setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  const { steps, byId } = useStepLibrary(log, asset);

  const addToWorkflow = (step) => setWorkflow((prev) => [...prev, step.id]);
  const clearWorkflow = () => setWorkflow([]);
  const removeFromWorkflow = (index) =>
    setWorkflow((prev) => prev.filter((_, i) => i !== index));

  const runStep = async (step) => {
    setBusy(true);
    try {
      log(`▶︎ ${step.title}`);
      await step.run();
      log(`✔ ${step.id} done`);
    } catch (e) {
      console.error(e);
      log(`✖ ${step.id} failed: ${e.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  const runWorkflow = async () => {
    for (const id of workflow) {
      await runStep(byId[id]);
    }
  };

  return (
    <MainCard title="Sonic Labs">
      <Stack spacing={2}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="body2">Profile</Typography>
          <Chip label={DEDICATED_ALIAS} size="small" />
          <Box sx={{ flexGrow: 1 }} />
          <ToggleButtonGroup
            value={asset}
            exclusive
            size="small"
            onChange={(_, v) => v && setAsset(v)}
          >
            <ToggleButton value="SOL">SOL</ToggleButton>
            <ToggleButton value="ETH">ETH</ToggleButton>
            <ToggleButton value="WBTC">WBTC</ToggleButton>
          </ToggleButtonGroup>
        </Stack>
        <Typography variant="h6">Step Library</Typography>
        <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap' }}>
          {steps.map((s) => (
            <StepCard
              key={s.id}
              step={s}
              onRun={runStep}
              onAdd={addToWorkflow}
              disabled={busy}
            />
          ))}
        </Stack>

        <Divider />

        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Workflow
          </Typography>
          <Button
            size="small"
            onClick={runWorkflow}
            disabled={busy || workflow.length === 0}
          >
            Run
          </Button>
          <Button
            size="small"
            onClick={clearWorkflow}
            disabled={busy || workflow.length === 0}
          >
            Clear
          </Button>
        </Stack>

        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          {workflow.map((id, idx) => (
            <Chip
              key={`${id}-${idx}`}
              label={byId[id].title}
              onDelete={() => removeFromWorkflow(idx)}
            />
          ))}
        </Stack>

        <LogConsole lines={logs} />
      </Stack>
    </MainCard>
  );
}

