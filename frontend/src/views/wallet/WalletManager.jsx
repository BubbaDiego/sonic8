import { useMemo, useState, useEffect } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import { Grid, Button, IconButton, Avatar, Stack, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
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

const STALE_MS = 10 * 60 * 1000;

const WalletManager = () => {
  const { wallets = [], walletsLoading } = useGetWallets();
  const loading = walletsLoading;
  const [modalOpen, setModalOpen] = useState(false);
  const [editWallet, setEditWallet] = useState(null);

  // verified state: { [address]: { data, at, error } }
  const [verifiedMap, setVerifiedMap] = useState({});
  const [verifying, setVerifying] = useState(new Set());
  const [pieSource, setPieSource] = useState('positions'); // 'positions' | 'verified'

  const setVerifyingAddr = (addr, on) => {
    setVerifying((prev) => {
      const next = new Set(prev);
      on ? next.add(addr) : next.delete(addr);
      return next;
    });
  };

  const verifyOne = async (addr, { force = false } = {}) => {
    const a = (addr || '').trim();
    if (!a) return;
    setVerifyingAddr(a, true);
    try {
      const res = await fetch('/api/wallets/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: a, force })
      });
      const json = await res.json();
      setVerifiedMap((m) => ({
        ...m,
        [a]: { data: json, at: Date.now(), error: json?.error ? json.detail || 'error' : null }
      }));
    } catch (e) {
      setVerifiedMap((m) => ({ ...m, [a]: { data: null, at: Date.now(), error: String(e) } }));
    } finally {
      setVerifyingAddr(a, false);
    }
  };

  const verifyAll = async () => {
    const addrs = wallets.map((w) => (w.public_address || '').trim()).filter(Boolean);
    if (!addrs.length) return;
    addrs.forEach((a) => setVerifyingAddr(a, true));
    try {
      const res = await fetch('/api/wallets/verify-bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ addresses: addrs, force: false })
      });
      const json = await res.json();
      const now = Date.now();
      const next = {};
      addrs.forEach((a) => {
        next[a] = { data: json[a], at: now, error: json[a]?.error ? json[a].detail || 'error' : null };
      });
      setVerifiedMap((m) => ({ ...m, ...next }));
    } catch (e) {
      const now = Date.now();
      const next = {};
      addrs.forEach((a) => {
        next[a] = { data: null, at: now, error: String(e) };
      });
      setVerifiedMap((m) => ({ ...m, ...next }));
    } finally {
      addrs.forEach((a) => setVerifyingAddr(a, false));
    }
  };

  const rows = useMemo(() => {
    return (wallets || []).map((w) => {
      const a = (w.public_address || '').trim();
      const v = verifiedMap[a];
      const d = v?.data && !v.data.error ? v.data : null;
      const verifiedSol = d?.totals?.solIncludingRent ?? null;
      const rentLamports = d?.tokenAccountsLamports ?? 0;
      const top = d?.top || [];
      const at = v?.at || null;
      const error = v?.error || null;
      const isVerifying = verifying.has(a);
      const stale = at ? Date.now() - at > STALE_MS : false;
      return {
        ...w,
        _addr: a,
        verifiedSol,
        rentLamports,
        top,
        verifiedAt: at,
        verifyError: error,
        isVerifying,
        stale
      };
    });
  }, [wallets, verifiedMap, verifying]);

  useEffect(() => {
    const id = setInterval(() => {
      verifyAll();
    }, 10 * 60 * 1000);
    verifyAll();
    return () => clearInterval(id);
  }, [rows.length]);

  const walletsForPie = useMemo(() => {
    if (pieSource === 'positions') return wallets;
    return rows.map((r) => ({ ...r, balance: r.verifiedSol || 0 }));
  }, [pieSource, wallets, rows]);

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

  if (loading) return <MainCard><Typography>Loading…</Typography></MainCard>;

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={8}>
        <MainCard
          title="💼 Wallet Manager"
          secondary={
            <Stack direction="row" spacing={1}>
              <Button onClick={handleAdd} variant="contained">Add</Button>
              <IconButton onClick={handleStarWars} size="large">
                <Avatar src="/images/yoda_icon.jpg" sx={{ width: 32, height: 32 }} />
              </IconButton>
            </Stack>
          }
        >
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <WalletTable
                rows={rows}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onVerifyAll={verifyAll}
                onVerifyOne={verifyOne}
              />
            </Grid>
          </Grid>

          <WalletFormModal
            open={modalOpen}
            mode={editWallet ? 'edit' : 'add'}
            initialValues={editWallet || { name: '', public_address: '', image_path: '', balance: 0, is_active: true, type: 'personal' }}
            onSubmit={handleSave}
            onClose={() => setModalOpen(false)}
          />
        </MainCard>
      </Grid>
      <Grid item xs={12} md={4}>
        <Stack spacing={1} direction="row" justifyContent="flex-end" sx={{ mb: 1 }}>
          <ToggleButtonGroup
            value={pieSource}
            exclusive
            onChange={(e, v) => v && setPieSource(v)}
            size="small"
          >
            <ToggleButton value="positions">Positions</ToggleButton>
            <ToggleButton value="verified">Verified</ToggleButton>
          </ToggleButtonGroup>
        </Stack>
        <BalanceBreakdownCard wallets={walletsForPie} />
      </Grid>
    </Grid>
  );
};

export default WalletManager;
