
import React from 'react';
import { Button, Stack, Typography, Avatar, AppBar, Toolbar } from '@mui/material';
import { IconRefresh, IconUpdate, IconTrash, IconTornado } from '@tabler/icons-react';

const Index = () => {
  return (
    <AppBar position="static" color="default" elevation={3}>
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Cyclone Run Actions
        </Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          <Button variant="outlined" startIcon={<IconRefresh size={20} />}>
            Price Update
          </Button>
          <Button variant="outlined" startIcon={<IconUpdate size={20} />}>
            Position Update
          </Button>
          <Button variant="outlined" color="error" startIcon={<IconTrash size={20} />}>
            Delete
          </Button>
          <Button variant="contained" color="primary" startIcon={<IconTornado size={20} />}>
            Full Cyclone
          </Button>
        </Stack>
      </Toolbar>
    </AppBar>
  );
};

export default Index;
