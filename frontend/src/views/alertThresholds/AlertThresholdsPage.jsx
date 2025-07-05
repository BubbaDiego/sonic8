import { useEffect } from 'react';
import { Grid, Button } from '@mui/material';
import MainCard from 'ui-component/cards/MainCard';
import ThresholdTable from 'ui-component/thresholds/ThresholdTable';
import CooldownTable from 'ui-component/thresholds/CooldownTable';
import { useDispatch, useSelector } from 'store';
import {
  fetchThresholds,
  persistThresholds,
  setThreshold,
  setCooldown
} from 'store/slices/alertThresholds';

export default function AlertThresholdsPage() {
  const dispatch = useDispatch();
  const { thresholds, cooldowns } = useSelector((state) => state.alertThresholds);

  useEffect(() => {
    dispatch(fetchThresholds());
  }, [dispatch]);

  const handleThresholdChange = (id, field, value) =>
    dispatch(setThreshold({ id, field, value }));

  const handleCooldownChange = (field, value) =>
    dispatch(setCooldown({ field, value }));

  const handleSave = () => {
    dispatch(persistThresholds());
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
