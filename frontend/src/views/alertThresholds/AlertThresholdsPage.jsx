import { useEffect } from 'react';
import { Grid, Button } from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';
import ThresholdTable from 'ui-component/thresholds/ThresholdTable';
import CooldownTable from 'ui-component/thresholds/CooldownTable';
import { useDispatch, useSelector } from 'store';
import { fetchThresholds, persistThresholds, setThresholds } from 'store/slices/alertThresholds';

export default function AlertThresholdsPage() {
  const dispatch = useDispatch();
  const { data } = useSelector((state) => state.thresholds);
  const thresholds = data?.thresholds || [];
  const cooldowns = data?.cooldowns || {};

  useEffect(() => {
    dispatch(fetchThresholds());
  }, [dispatch]);

  const handleThresholdChange = (id, field, value) => {
    const updated = thresholds.map((t) =>
      t.id === id ? { ...t, [field]: value } : t
    );
    dispatch(setThresholds({ thresholds: updated, cooldowns }));
  };

  const handleCooldownChange = (field, value) => {
    const updated = { ...cooldowns, [field]: value };
    dispatch(setThresholds({ thresholds, cooldowns: updated }));
  };

  const handleSave = () => {
    dispatch(persistThresholds({ thresholds, cooldowns }));
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <MainCard title="Alert Thresholds" secondary={<Button variant="contained" onClick={handleSave}>Save All</Button>}>
          <ThresholdTable rows={thresholds} onChange={handleThresholdChange} />
          <div style={{ height: 16 }} />
          <CooldownTable values={cooldowns} onChange={handleCooldownChange} />
        </MainCard>
      </Grid>
    </Grid>
  );
}
