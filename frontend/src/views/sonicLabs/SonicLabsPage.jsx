import MainCard from 'ui-component/cards/MainCard';
import { Typography, Button } from '@mui/material';
import { useState } from 'react';

const SonicLabsPage = () => {
  const [status, setStatus] = useState('');

  const handleClick = async () => {
    setStatus('⏳ launching…');
    try {
      const res = await fetch('/api/auto-core/open-browser', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://example.com' })
      });
      const data = await res.json();
      setStatus(`✅ opened → ${data.title}`);
    } catch (err) {
      console.error(err);
      setStatus('❌ failed – see console');
    }
  };

  return (
    <MainCard title="Sonic Labs">
      <Typography variant="body1" gutterBottom>
        Welcome to Sonic Labs.
      </Typography>
      <Button variant="contained" onClick={handleClick}>
        Launch test browser
      </Button>
      {status && (
        <Typography variant="caption" display="block" sx={{ mt: 1 }}>
          {status}
        </Typography>
      )}
    </MainCard>
  );
};

export default SonicLabsPage;
