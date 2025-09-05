import MainCard from 'ui-component/cards/MainCard';
import { Typography, Button, Stack, Card, CardContent, CardActions, Chip, Divider, Box } from '@mui/material';
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

function useStepLibrary(log) {
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
      id: 'connect-solflare',
      title: 'Connect to Jupiter (Solflare)',
      desc: 'Click Connect → Solflare and approve in the extension popup.',
      run: async () => {
        const r = await apiPost('/jupiter/connect/solflare');
        log(JSON.stringify(r));
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
  ]), [log]);

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
  const [workflow, setWorkflow] = useState([]); // array of step ids in order

  const log = (msg) => setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  const { steps, byId } = useStepLibrary(log);

  const addToWorkflow = (step) => setWorkflow((prev) => [...prev, step.id]);
  const clearWorkflow = () => setWorkflow([]);

  const runStep = async (step) => {
    setBusy(true);
    try {
      log(`▶︎ ${step.title}`);
      await step.run();
      log(`✔ ${step.id} do
