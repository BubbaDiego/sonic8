import { useState, useEffect } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import SyncIcon from '@mui/icons-material/Sync';
import ProviderAccordion from './components/ProviderAccordion';
import { useProviders, useSaveProviders, useStatus, useTestMessage, useRunHeartbeat } from 'hooks/useXCom';
import { enqueueSnackbar } from 'notistack';

const emailFields = [
  { key: 'server', label: 'SMTP Server', placeholder: 'smtp.gmail.com' },
  { key: 'port', label: 'Port', placeholder: '587' },
  { key: 'username', label: 'Username', placeholder: 'you@gmail.com' },
  { key: 'password', label: 'Password', placeholder: 'your_password' },
  { key: 'default_recipient', label: 'Default Recipient', placeholder: 'team@example.com' }
];

const twilioFields = [
  { key: 'account_sid', label: 'Account SID' },
  { key: 'auth_token', label: 'Auth Token' },
  { key: 'flow_sid', label: 'Flow SID' },
  { key: 'default_from_phone', label: 'From Phone' },
  { key: 'default_to_phone', label: 'To Phone' }
];

export default function XComSettings() {
  const { data: providers, isLoading: providersLoading, error: providersError } = useProviders();
  const saveProviders = useSaveProviders();
  const { data: status, refetch: refetchStatus, isLoading: statusLoading } = useStatus();
  const runHeartbeat = useRunHeartbeat();
  const testMsg = useTestMessage();

  const [draft, setDraft] = useState({});

  useEffect(() => {
    if (providers) setDraft(JSON.parse(JSON.stringify(providers)));
  }, [providers]);

  const handleSave = () => {
    saveProviders.mutate(draft, {
      onSuccess: () => enqueueSnackbar('Settings saved', { variant: 'success' }),
      onError: (err) => enqueueSnackbar('Save failed: ' + err.message, { variant: 'error' })
    });
  };

  const runTest = (mode) => {
    testMsg.mutate({ mode }, {
      onSuccess: (res) => enqueueSnackbar('Test ' + mode + ' sent (' + (res.success ? 'ok' : 'error') + ')', { variant: res.success ? 'success' : 'error' }),
      onError: (err) => enqueueSnackbar('Test failed: ' + err.message, { variant: 'error' })
    });
  };

  if (providersLoading || statusLoading) return <CircularProgress />;
  if (providersError) return <div>Error loading providers: {providersError.message}</div>;

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={6}>
        <MainCard title="Provider Settings">
          <ProviderAccordion
            title="Email (SMTP)"
            fields={emailFields}
            values={draft.email?.smtp || {}}
            onChange={(update) => setDraft(prev => ({
              ...prev,
              email: { ...prev.email, smtp: update }
            }))}
          />
          <ProviderAccordion
            title="Twilio (API)"
            fields={twilioFields}
            values={draft.api || {}}
            onChange={(update) => setDraft(prev => ({ ...prev, api: update }))}
          />

          <Stack direction="row" spacing={2} justifyContent="flex-end" sx={{ mt: 2 }}>
            <Button variant="outlined" onClick={() => setDraft(providers)}>Cancel</Button>
            <Button variant="contained" onClick={handleSave} disabled={saveProviders.isLoading}>Save</Button>
          </Stack>
        </MainCard>
      </Grid>

      <Grid item xs={12} md={6}>
        <Stack spacing={3}>
          <MainCard title="Provider Status" secondary={
            <Button size="small" onClick={refetchStatus}><SyncIcon /></Button>
          }>
            <List>
              {['twilio', 'smtp', 'chatgpt', 'jupiter', 'github'].map(key => {
                const st = status?.[key] || '—';
                const ok = st === 'ok';
                return (
                  <ListItem key={key}>
                    <ListItemIcon>{ok ? <CheckCircleIcon color="success" /> : <ErrorIcon color="error" />}</ListItemIcon>
                    <ListItemText primary={key.toUpperCase()} secondary={st} />
                  </ListItem>
                )
              })}
            </List>
          </MainCard>

          <MainCard title="Send Test Notification">
            <Stack direction="row" spacing={2}>
              {['voice', 'email', 'sound'].map(mode => (
                <Button
                  key={mode}
                  variant="outlined"
                  onClick={() => runTest(mode)}
                  disabled={testMsg.isLoading}
                >
                  Test {mode}
                </Button>
              ))}
            </Stack>
          </MainCard>

          <MainCard title="Heartbeat">
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                onClick={() => runHeartbeat.mutate()}
                disabled={runHeartbeat.isLoading}
              >
                Run Heartbeat Now
              </Button>
            </Stack>
          </MainCard>
        </Stack>
      </Grid>
    </Grid>
  );
}
