// material-ui
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

export default function Footer() {
  return (
    <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'center', pt: 3, mt: 'auto' }}>
      <Typography variant="caption">&copy; All rights reserved Sonic1</Typography>
    </Stack>
  );
}
