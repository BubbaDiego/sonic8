import React, { useState } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import { Grid, Button, IconButton, Avatar, Stack } from '@mui/material';
import WalletTable from 'ui-component/wallet/WalletTable';
import WalletFormModal from 'ui-component/wallet/WalletFormModal';
import BalanceBreakdownCard from './BalanceBreakdownCard';
import {
  useGetWallets,
  createWallet,
  updateWallet,
  deleteWallet,
  refreshWallets,
  insertStarWarsWallets
} from 'api/wallets';

const WalletManager = () => {
  const { wallets = [] } = useGetWallets();
  const [modalOpen, setModalOpen] = useState(false);
  const [editWallet, setEditWallet] = useState(null);

  const handleAdd = () => {
    setEditWallet(null);
    setModalOpen(true);
  };

  const handleEdit = (w) => {
    setEditWallet(w);
    setModalOpen(true);
  };

  const handleSave = async (w) => {
    if (editWallet) {
      await updateWallet(editWallet.name, w);
    } else {
      await createWallet(w);
    }
    refreshWallets();
  };

  const handleDelete = async (name) => {
    await deleteWallet(name);
    refreshWallets();
  };

  const handleStarWars = async () => {
    await insertStarWarsWallets();
    refreshWallets();
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={8}>
        <MainCard
          title="💼 Wallet Manager"
          secondary={
            <Stack direction="row" spacing={1}>
              <Button onClick={handleAdd} variant="contained">Add</Button>
              <IconButton onClick={handleStarWars} size="large">
                <Avatar src="/static/images/yoda_icon.jpg" sx={{ width: 32, height: 32 }} />
              </IconButton>
            </Stack>
          }
        >
          <Grid container spacing={2}>
              <Grid item xs={12}>
                <WalletTable rows={wallets} onEdit={handleEdit} onDelete={handleDelete}/>
              </Grid>
          </Grid>

          <WalletFormModal
            open={modalOpen}
            mode={editWallet ? 'edit' : 'add'}
            initialValues={editWallet || {name:'', public_address:'', image_path:'', balance:0, is_active:true, type:'personal'}}
            onSubmit={handleSave}
            onClose={()=> setModalOpen(false)}
          />
        </MainCard>
      </Grid>
      <Grid item xs={12} md={4}>
        <BalanceBreakdownCard wallets={wallets} />
      </Grid>
    </Grid>
  );
};

export default WalletManager;
