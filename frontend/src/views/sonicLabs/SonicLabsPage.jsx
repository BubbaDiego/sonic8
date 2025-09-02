import MainCard from 'ui-component/cards/MainCard';
import { Typography, Button, Stack } from '@mui/material';
import { useState } from 'react';

const SonicLabsPage = () => {
  const [status, setStatus] = useState('');

  const openJupiter = async () => {
    setStatus('⏳ Opening Jupiter and clicking Connect…');
    try {
      const res = await fetch('/api/auto-core/connect-jupiter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: 'https://jup.ag/perps',
          wallet: 'solflare'
        })
      });
      const data = await res.json();
      if (data.error) {
        setStatus(`❌ ${data.error}: ${data.detail || ''}`);
      } else {
        const wallet = data.wallet_clicked ? ` (wallet: ${data.selected_wallet})` : '';
        setStatus(`✅ ${data.status}${wallet} → ${data.title}`);
      }
    } catch (err) {
      console.error(err);
      setStatus('❌ failed – see console');
    }
  };

  const closeBrowser = async () => {
    setStatus('⏳ Closing browser…');
    try {
      const res = await fetch('/api/auto-core/close-browser', { method: 'POST' });
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
