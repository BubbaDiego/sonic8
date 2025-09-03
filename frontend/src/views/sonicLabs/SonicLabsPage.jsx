import MainCard from 'ui-component/cards/MainCard';
import { Typography, Button, Stack, TextField } from '@mui/material';
import { useState } from 'react';

const SonicLabsPage = () => {
  const [status, setStatus] = useState('');
  const [walletId, setWalletId] = useState('default'); // pick your alias (e.g., "connie")

  const openJupiter = async () => {
    setStatus('⏳ Opening Jupiter…');
    try {
      const res = await fetch('/jupiter/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ walletId })
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setStatus(`✅ launched ${data.launched}`);
      } else {
        setStatus(`❌ failed to launch`);
      }
    } catch (err) {
      console.error(err);
      setStatus('❌ failed – see console');
    }
  };

  const closeBrowser = async () => {
    setStatus('⏳ Closing browser…');
    try {
      // Close only the selected wallet context; keep the global close as a separate button if you want.
      const res = await fetch('/api/auto-core/close-wallet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_id: walletId })
      });
      const data = await res.json();
      if (data.error) setStatus(`❌ ${data.error}: ${data.detail || ''}`);
      else setStatus('✅ Browser closed');
    } catch (err) {
      console.error(err);
      setStatus('❌ failed to close – see console');
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
        <Button variant="contained" color="primary" onClick={openJupiter}>
          Open Jupiter & Connect
        </Button>
        <Button variant="outlined" color="secondary" onClick={closeBrowser}>
          Close Browser
        </Button>
      </Stack>
    </MainCard>
  );
};

export default SonicLabsPage;
