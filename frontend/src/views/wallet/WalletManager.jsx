import React, { useState } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import { Grid, Button } from '@mui/material';
import { wallets as mockWallets } from 'data/wallets';
import WalletTable from 'ui-component/wallet/WalletTable';
import WalletFormModal from 'ui-component/wallet/WalletFormModal';
import CollateralPanel from 'ui-component/wallet/CollateralPanel';

const WalletManager = () => {
  const [wallets, setWallets] = useState(mockWallets);
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

  const handleSave = (w) => {
    setWallets((prev)=>{
      const idx = prev.findIndex(p=>p.name===w.name);
      if(idx>-1){
        const cp=[...prev]; cp[idx]=w; return cp;
      }
      return [...prev, w];
    });
  };

  const handleDelete = (name) => {
    setWallets((prev)=> prev.filter(p=>p.name!==name));
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
