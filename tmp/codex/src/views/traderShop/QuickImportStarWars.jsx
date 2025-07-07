// src/views/traderShop/QuickImportStarWars.jsx
import React, { useState } from 'react';
import { Button } from '@mui/material';
import { importStarWarsTraders } from './hooks';

function QuickImportStarWars() {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    setLoading(true);
    try {
      await importStarWarsTraders();
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      variant="outlined"
      size="small"
      onClick={handleClick}
      disabled={loading}
      sx={{ ml: 1 }}
    >
      Import Star Wars
    </Button>
  );
}

export default QuickImportStarWars;
