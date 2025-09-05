import MainCard from 'ui-component/cards/MainCard';
import { Typography, Button, Stack } from '@mui/material';
import { useState, useMemo } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? '/api' : '');
const DEDICATED_ALIAS = import.meta.env.VITE_AUTOPROFILE || 'Sonic - Auto';

async function apiPost(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined
  });
  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    console.error('apiPost: invalid JSON', raw);
    throw err;
  }
  if (!res.ok) {
    console.error('apiPost failed', res.status, data);
    throw new Error(data.detail || data.error || raw || res.statusText);
  }
  return data;
}

function useStepLibrary(log) {
  const steps = useMemo(() => ([
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
      id: 'open',
      title: 'Open dedicated browser',
      desc: `Launch Chrome with profile "${DEDICATED_ALIAS}" and open Jupiter.`,
      run: async () => {
        const r = await apiPost('/jupiter/open', { walletId: DEDICATED_ALIAS });
        log(JSON.stringify(r));
        return r;
      }
    },
    {
      id: 'close',
      title: 'Close browser',
      desc: 'Close the automation browser.',
      run: async () => {
        const r = await apiPost('/jupiter/close', { walletId: DEDICATED_ALIAS });
        log(JSON.stringify(r));
        return r;
      }
    }
  ]), [log]);
  return steps;
}

const SonicLabsPage = () => {
  const [status, setStatus] = useState('');
  const steps = useStepLibrary((msg) => setStatus(msg));

  return (
    <MainCard title="Sonic Labs">
      <Typography variant="body1" sx={{ mb: 2 }}>
        {status || 'Ready'}
      </Typography>
      <Stack spacing={2}>
        {steps.map((s) => (
          <Stack key={s.id} direction="row" spacing={2} alignItems="center">
            <Stack sx={{ flexGrow: 1 }}>
              <Typography variant="h6">{s.title}</Typography>
              <Typography variant="body2">{s.desc}</Typography>
            </Stack>
            <Button variant="contained" onClick={s.run}>Run</Button>
          </Stack>
        ))}
      </Stack>
    </MainCard>
  );
};

export default SonicLabsPage;
