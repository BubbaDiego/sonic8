import React, { useState } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import { Grid, Button } from '@mui/material';
import WalletTable from 'ui-component/wallet/WalletTable';
import WalletFormModal from 'ui-component/wallet/WalletFormModal';
import CollateralPanel from 'ui-component/wallet/CollateralPanel';
import {
  useGetWallets,
  createWallet,
  updateWallet,
  deleteWallet,
  refreshWallets
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

  return (
    <MainCard title="💼 Wallet Manager" secondary={<Button onClick={handleAdd} variant="contained">Add</Button>}>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <WalletTable rows={wallets} onEdit={handleEdit} onDelete={handleDelete}/>
        </Grid>
        <Grid item xs={12}>
          <CollateralPanel wallets={wallets}/>
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
  );
};

export default WalletManager;
