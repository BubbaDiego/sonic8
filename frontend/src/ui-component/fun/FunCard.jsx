
import { useEffect, useState } from 'react';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

export default function FunCard() {
  const [mode, setMode] = useState('joke'); // 'joke' | 'trivia' | 'quote'
  const [text, setText] = useState('Loading…');

  useEffect(() => {
    let cancel = false;
    async function fetchFun() {
      try {
        const res = await fetch(`/api/fun/random?type=${mode}`);
        if (!res.ok) throw new Error('Network error');
        const json = await res.json();
        if (!cancel) setText(json.text);
      } catch (err) {
        if (!cancel) setText('😢 Failed to load fun content.');
      }
    }
    fetchFun();
    const id = setInterval(fetchFun, 15000);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, [mode]);

  return (
    <Card>
      <CardContent>
        <ToggleButtonGroup value={mode} exclusive
          onChange={(_, v) => v && setMode(v)} size="small">
          <ToggleButton value="joke">Joke</ToggleButton>
          <ToggleButton value="trivia">Trivia</ToggleButton>
          <ToggleButton value="quote">Quote</ToggleButton>
        </ToggleButtonGroup>
        <Typography sx={{ mt: 2 }}>{text}</Typography>
      </CardContent>
    </Card>
  );
}
