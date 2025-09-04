import MainCard from 'ui-component/cards/MainCard';
import { Typography, Button, Stack, TextField } from '@mui/material';
import { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE || (import.meta.env.DEV ? '/api' : '');

async function openWallet(walletId) {
  const res = await fetch(`${API_BASE}/jupiter/open`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ walletId })
  });

  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    console.error('openWallet: invalid JSON', raw);
    throw err;
  }

  if (!res.ok) {
    console.error('openWallet failed', res.status, data);
    throw new Error(data.detail || data.error || raw || res.statusText);
  }

  return data;
}

async function closeWallet(walletId) {
  const res = await fetch(`${API_BASE}/jupiter/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(walletId ? { walletId } : {})
  });

  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    console.error('closeWallet: invalid JSON', raw);
    throw err;
  }

  if (!res.ok) {
    console.error('closeWallet failed', res.status, data);
    throw new Error(data.detail || data.error || raw || res.statusText);
  }

  return data;
}

const SonicLabsPage = () => {
  const [status, setStatus] = useState('');
  const [walletId, setWalletId] = useState('default'); // pick your alias (e.g., "connie")

  const onOpenClick = async () => {
    setStatus('⏳ Opening Jupiter…');
    try {
      const data = await openWallet(walletId);
      setStatus(`✅ launched ${data.pid ?? data.launched}`);
    } catch (err) {
      console.error(err);
      if (err instanceof Error && err.message) setStatus(`❌ ${err.message}`);
      else setStatus('❌ failed – see console');
    }
  };

  const onCloseClick = async () => {
    setStatus('⏳ Closing browser…');
    try {
      await closeWallet(walletId || undefined);
      setStatus('✅ closed');
    } catch (err) {
      console.error(err);
      if (err instanceof Error && err.message) setStatus(`❌ ${err.message}`);
      else setStatus('❌ failed – see console');
    }
  };

  return (
    <MainCard title="Sonic Labs">
      <Typography variant="body1" sx={{ mb: 2 }}>
        {status || 'Ready'}
      </Typography>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField
          label="Wallet ID"
          size="small"
          value={walletId}
          onChange={(e) => setWalletId(e.target.value)}
          helperText="Choose an alias you registered (e.g., connie, a0, jup-main)"
        />
      </Stack>
      <Stack direction="row" spacing={2}>
        <Button variant="contained" color="primary" onClick={onOpenClick}>
          Open Jupiter & Connect
        </Button>
        <Button variant="outlined" color="secondary" onClick={onCloseClick}>
          Close Browser
        </Button>
      </Stack>
    </MainCard>
  );
};

export default SonicLabsPage;
