import { useEffect, useMemo, useState } from 'react';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Skeleton from '@mui/material/Skeleton';
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';
import RefreshIcon from '@mui/icons-material/Refresh';
import CampaignIcon from '@mui/icons-material/Campaign';

import MainCard from 'ui-component/cards/MainCard';
import ProviderAccordion from './components/ProviderAccordion';
import { useProviders, useSaveProviders, useStatus, useTestMessage, useRunHeartbeat } from 'hooks/useXCom';
import { enqueueSnackbar } from 'notistack';

const cloneProviders = (data) => JSON.parse(JSON.stringify(data || {}));

const emailFields = [
  {
    key: 'enabled',
    label: 'Enable email notifications',
    type: 'switch',
    helperText: 'Toggle SMTP email delivery for alerts.'
  },
  {
    key: 'server',
    label: 'SMTP server',
    placeholder: 'smtp.gmail.com'
  },
  {
    key: 'port',
    label: 'Port',
    type: 'number',
    placeholder: '587'
  },
  {
    key: 'username',
    label: 'Username',
    placeholder: 'alerts@example.com'
  },
  {
    key: 'password',
    label: 'Password',
    placeholder: '••••••••'
  },
  {
    key: 'default_recipient',
    label: 'Default recipient',
    placeholder: 'team@example.com',
    fullWidth: true
  }
];

const twilioFields = [
  {
    key: 'enabled',
    label: 'Enable Twilio voice/SMS',
    type: 'switch',
    helperText: 'Uses the Twilio Studio flow for automated calls and texts.'
  },
  {
    key: 'account_sid',
    label: 'Account SID',
    placeholder: 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  },
  {
    key: 'auth_token',
    label: 'Auth token',
    placeholder: '••••••••'
  },
  {
    key: 'flow_sid',
    label: 'Studio flow SID',
    placeholder: 'FWxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  },
  {
    key: 'default_from_phone',
    label: 'From phone number',
    placeholder: '+15555551234'
  },
  {
    key: 'default_to_phone',
    label: 'Default recipient phone',
    placeholder: '+15555559876'
  }
];

const ttsFields = [
  {
    key: 'enabled',
    label: 'Enable text-to-speech',
    type: 'switch',
    helperText: 'Requires the optional pyttsx3 dependency.'
  },
  {
    key: 'voice',
    label: 'Voice',
    placeholder: 'Hazel'
  },
  {
    key: 'speed',
    label: 'Speech rate (wpm)',
    type: 'number',
    placeholder: '140'
  }
];

const STATUS_LABELS = {
  smtp: 'SMTP',
  twilio: 'Twilio',
  sound: 'Sound'
};

const formatStatusLabel = (key) => STATUS_LABELS[key] || key.toUpperCase();

const createEmailValues = (draft) => ({
  enabled: Boolean(draft?.email?.enabled),
  server: draft?.email?.smtp?.server ?? '',
  port: draft?.email?.smtp?.port ?? '',
  username: draft?.email?.smtp?.username ?? '',
  password: draft?.email?.smtp?.password ?? '',
  default_recipient: draft?.email?.smtp?.default_recipient ?? ''
});

const createTwilioValues = (draft) => ({
  enabled: Boolean(draft?.twilio?.enabled ?? draft?.api?.enabled),
  account_sid: draft?.twilio?.account_sid ?? draft?.api?.account_sid ?? '',
  auth_token: draft?.twilio?.auth_token ?? draft?.api?.auth_token ?? '',
  flow_sid: draft?.twilio?.flow_sid ?? draft?.api?.flow_sid ?? '',
  default_from_phone: draft?.twilio?.default_from_phone ?? draft?.api?.default_from_phone ?? '',
  default_to_phone: draft?.twilio?.default_to_phone ?? draft?.api?.default_to_phone ?? ''
});

const createTTSValues = (draft) => ({
  enabled: Boolean(draft?.tts?.enabled),
  voice: draft?.tts?.voice ?? '',
  speed: draft?.tts?.speed ?? ''
});

export default function XComSettings() {
  const { data: providers, isLoading: providersLoading, error: providersError } = useProviders();
  const saveProviders = useSaveProviders();
  const {
    data: status,
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus,
    dataUpdatedAt: statusUpdatedAt
  } = useStatus();
  const runHeartbeat = useRunHeartbeat();
  const testMessage = useTestMessage();

  const [draft, setDraft] = useState({});

  useEffect(() => {
    if (providers) {
      setDraft(cloneProviders(providers));
    }
  }, [providers]);

  const serializedProviders = useMemo(() => JSON.stringify(providers || {}), [providers]);
  const serializedDraft = useMemo(() => JSON.stringify(draft || {}), [draft]);
  const isDirty = serializedProviders !== serializedDraft;

  const handleEmailChange = (values) => {
    setDraft((prev) => ({
      ...(prev || {}),
      email: {
        ...(prev?.email || {}),
        enabled: Boolean(values.enabled),
        smtp: {
          ...(prev?.email?.smtp || {}),
          server: values.server,
          port: values.port === '' ? '' : Number(values.port),
          username: values.username,
          password: values.password,
          default_recipient: values.default_recipient
        }
      }
    }));
  };

  const handleTwilioChange = (values) => {
    setDraft((prev) => ({
      ...(prev || {}),
      twilio: {
        ...(prev?.twilio || prev?.api || {}),
        enabled: Boolean(values.enabled),
        account_sid: values.account_sid,
        auth_token: values.auth_token,
        flow_sid: values.flow_sid,
        default_from_phone: values.default_from_phone,
        default_to_phone: values.default_to_phone
      }
    }));
  };

  const handleTTSChange = (values) => {
    setDraft((prev) => ({
      ...(prev || {}),
      tts: {
        ...(prev?.tts || {}),
        enabled: Boolean(values.enabled),
        voice: values.voice,
        speed: values.speed === '' ? '' : Number(values.speed)
      }
    }));
  };

  const handleReset = () => {
    setDraft(cloneProviders(providers || {}));
  };

  const handleSave = () => {
    if (!draft) return;
    saveProviders.mutate(draft, {
      onSuccess: () => {
        enqueueSnackbar('Provider settings saved', { variant: 'success' });
      },
      onError: (err) => {
        enqueueSnackbar(`Unable to save settings: ${err.message || err}`, { variant: 'error' });
      }
    });
  };

  const handleTest = (mode) => {
    testMessage.mutate(
      { mode },
      {
        onSuccess: (result) => {
          if (result?.success) {
            enqueueSnackbar(`Test ${mode} notification sent`, { variant: 'success' });
          } else {
            enqueueSnackbar(`Test ${mode} reported an error`, { variant: 'warning' });
          }
        },
        onError: (err) => {
          enqueueSnackbar(`Test ${mode} failed: ${err.message || err}`, { variant: 'error' });
        }
      }
    );
  };

  const handleRunHeartbeat = () => {
    runHeartbeat.mutate(undefined, {
      onSuccess: () => {
        enqueueSnackbar('Heartbeat triggered', { variant: 'info' });
      },
      onError: (err) => {
        enqueueSnackbar(`Heartbeat failed: ${err.message || err}`, { variant: 'error' });
      }
    });
  };

  const statusEntries = useMemo(() => Object.entries(status || {}), [status]);
  const lastChecked = statusUpdatedAt ? new Date(statusUpdatedAt).toLocaleString() : null;

  const providersCardBody = () => {
    if (providersError) {
      return <Alert severity="error">{providersError.message || 'Unable to load provider settings'}</Alert>;
    }

    if (providersLoading && !providers) {
      return (
        <Stack spacing={2}>
          <Skeleton variant="rounded" height={64} />
          <Skeleton variant="rounded" height={64} />
          <Skeleton variant="rounded" height={48} />
        </Stack>
      );
    }

    return (
      <Stack spacing={1.5}>
        <ProviderAccordion
          title="Email (SMTP)"
          description="XCom uses SMTP to deliver email alerts."
          fields={emailFields}
          values={createEmailValues(draft)}
          onChange={handleEmailChange}
          defaultExpanded
        />
        <ProviderAccordion
          title="Twilio"
          description="Configure Twilio credentials used for automated calls and SMS."
          fields={twilioFields}
          values={createTwilioValues(draft)}
          onChange={handleTwilioChange}
        />
        <ProviderAccordion
          title="Text-to-Speech"
          description="Optional local speech synthesis for audible alerts."
          fields={ttsFields}
          values={createTTSValues(draft)}
          onChange={handleTTSChange}
        />
        <Divider />
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} justifyContent="flex-end">
          <Button variant="outlined" onClick={handleReset} disabled={!isDirty || saveProviders.isLoading}>
            Reset
          </Button>
          <Button variant="contained" onClick={handleSave} disabled={!isDirty || saveProviders.isLoading}>
            {saveProviders.isLoading ? <CircularProgress size={22} /> : 'Save changes'}
          </Button>
        </Stack>
      </Stack>
    );
  };

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} lg={7}>
        <MainCard title="Provider settings">{providersCardBody()}</MainCard>
      </Grid>
      <Grid item xs={12} lg={5}>
        <Stack spacing={3}>
          <MainCard
            title="Status"
            secondary={
              <Tooltip title="Refresh now">
                <span>
                  <Button
                    startIcon={<RefreshIcon />}
                    size="small"
                    variant="outlined"
                    onClick={() => refetchStatus()}
                    disabled={statusLoading}
                  >
                    Refresh
                  </Button>
                </span>
              </Tooltip>
            }
          >
            <Stack spacing={1.5}>
              {statusError ? (
                <Alert severity="error">{statusError.message || 'Unable to fetch provider status'}</Alert>
              ) : null}

              {statusLoading && statusEntries.length === 0 ? (
                <Stack spacing={1}>
                  <Skeleton variant="rounded" height={40} />
                  <Skeleton variant="rounded" height={40} />
                </Stack>
              ) : null}

              {!statusLoading && statusEntries.length === 0 ? (
                <Typography color="text.secondary">No status data available yet.</Typography>
              ) : null}

              {statusEntries.map(([key, value]) => {
                const normalized = (value || '').toString();
                const ok = normalized.toLowerCase() === 'ok';
                const color = ok ? 'success' : normalized === 'timeout' ? 'warning' : 'error';
                return (
                  <Stack
                    key={key}
                    direction="row"
                    alignItems="center"
                    spacing={1.5}
                    sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, px: 1.5, py: 1 }}
                  >
                    <Chip color={color} label={formatStatusLabel(key)} variant={ok ? 'filled' : 'outlined'} />
                    <Typography variant="body2" color={ok ? 'success.main' : 'text.primary'}>
                      {normalized}
                    </Typography>
                  </Stack>
                );
              })}

              {lastChecked ? (
                <Typography variant="caption" color="text.secondary">
                  Last checked {lastChecked}
                </Typography>
              ) : null}
            </Stack>
          </MainCard>

          <MainCard title="Send test notification">
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="flex-start">
              {['voice', 'email', 'sound'].map((mode) => (
                <Button
                  key={mode}
                  variant="outlined"
                  startIcon={<CampaignIcon />}
                  onClick={() => handleTest(mode)}
                  disabled={testMessage.isLoading}
                >
                  Test {mode}
                </Button>
              ))}
            </Stack>
          </MainCard>

          <MainCard title="Heartbeat">
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="center">
              <Button
                variant="contained"
                color="secondary"
                onClick={handleRunHeartbeat}
                disabled={runHeartbeat.isLoading}
              >
                {runHeartbeat.isLoading ? <CircularProgress size={22} color="inherit" /> : 'Run heartbeat now'}
              </Button>
              <Typography variant="body2" color="text.secondary">
                Executes the XCom monitor immediately and refreshes status once complete.
              </Typography>
            </Stack>
          </MainCard>
        </Stack>
      </Grid>
    </Grid>
  );
}
