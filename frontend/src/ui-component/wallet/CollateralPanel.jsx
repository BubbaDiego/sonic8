import React from 'react';
import { Button, Grid, TextField, MenuItem } from '@mui/material';
import { useFormik } from 'formik';

const CollateralForm = ({ wallets, mode }) => {
  const formik = useFormik({
    initialValues: { wallet_name: wallets[0]?.name || '', market: '', amount: '' },
    onSubmit: (v) => {
      console.log(mode, v);
    }
  });

  return (
    <form onSubmit={formik.handleSubmit}>
      <Grid container spacing={1} alignItems="center">
        <Grid item xs={12} md={4}>
          <TextField
            select
            fullWidth
            label="Wallet"
            name="wallet_name"
            value={formik.values.wallet_name}
            onChange={formik.handleChange}
          >
            {wallets.map((w) => (
              <MenuItem key={w.name} value={w.name}>{w.name}</MenuItem>
            ))}
          </TextField>
        </Grid>
        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            label="Market"
            name="market"
            value={formik.values.market}
            onChange={formik.handleChange}
            placeholder="SOL-PERP"
          />
        </Grid>
        <Grid item xs={12} md={3}>
          <TextField
            fullWidth
            type="number"
            label="Amount"
            name="amount"
            value={formik.values.amount}
            onChange={formik.handleChange}
          />
        </Grid>
        <Grid item xs={12} md={2}>
          <Button variant={mode==='deposit'?'contained':'outlined'} color={mode==='deposit'?'success':'warning'} type="submit" fullWidth>
            {mode==='deposit'?'Deposit':'Withdraw'}
          </Button>
        </Grid>
      </Grid>
    </form>
  );
};

const CollateralPanel = ({ wallets }) => (
  <>
    <CollateralForm wallets={wallets} mode="deposit" />
    <div style={{ height: 8 }} />
    <CollateralForm wallets={wallets} mode="withdraw" />
  </>
);

export default CollateralPanel;
