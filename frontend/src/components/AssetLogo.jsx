import React from 'react';
import Avatar from '@mui/material/Avatar';

export default function AssetLogo({ symbol, size = 24 }) {
  const src = `/images/${String(symbol || 'unknown').toLowerCase()}_logo.png`;
  return (
    <Avatar
      src={src}
      alt={symbol}
      sx={{ width: size, height: size }}
      onError={(e) => {
        e.currentTarget.onerror = null;
        e.currentTarget.src = '/images/unknown.png';
      }}
    />
  );
}
