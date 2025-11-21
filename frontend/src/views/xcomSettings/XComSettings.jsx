import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Skeleton from '@mui/material/Skeleton';
import Divider from '@mui/material/Divider';
import TextField from '@mui/material/TextField';
import RefreshIcon from '@mui/icons-material/Refresh';
import { Card, CardContent, CardHeader, Button, Stack, Tooltip, Box } from '@mui/material';
import { IconExternalLink, IconActivity, IconPhone, IconMail, IconVolume2 } from '@tabler/icons-react';

import MainCard from 'ui-component/cards/MainCard';
import ProviderAccordion from './components/ProviderAccordion';
import {
  useProviders,
  useProvidersResolved,
  useSaveProviders,
  useStatus,
  useTestMessage,
  useRunHeartbeat
} from 'hooks/useXCom';
import { enqueueSnackbar } from 'notistack';
import { resetCooldown, setCooldown as setCooldownApi, saveProviders as apiSaveProviders } from 'api/xcom';

const TWILIO_CONSOLE_URL = 'https://console.twilio.com/';
const TWILIO_CALL_LOG_URL = 'https://console.twilio.com/us1/monitor/logs/calls';

const TwilioIcon = (props) => (
  <Box
    component="img"
    src="/images/twilio.png"
    alt="Twilio"
    onError={(e) => {
      e.currentTarget.onerror = null;
      e.currentTarget.src = '/static/images/twilio.png';
    }}
    sx={{ width: 28, height: 28, borderRadius: '4px' }}
    {...props}
  />
);
const isE164 = (value) => /^\+[1-9]\d{6,14}$/.test(String(value ?? ''));
const pick = (...vals) => vals.find((v) => v !== undefined && v !== null && String(v).trim() !== '') || '';
const isTwilio = (provider) => {
  const key = (provider?.id || provider?.key || provider?.name || provider?.title || '')
    .toString()
    .toLowerCase();
  return key.includes('twilio') || key.includes('sms');
};
const sortTwilioFirst = (a, b) => {
  const aIsTwilio = isTwilio(a);
  const bIsTwilio = isTwilio(b);
  if (aIsTwilio && !bIsTwilio) return -1;
  if (!aIsTwilio && bIsTwilio) return 1;
  return 0;
};
const resolveStatus = (statusObj, provider) => {
  const candidates = [provider?.id, provider?.name, provider?.key, provider?.title]
    .filter(Boolean)
    .map((value) => value.toString().toLowerCase());
  for (const candidate of candidates) {
    const val = statusObj?.[candidate];
    if (typeof val === 'string') {
      return val.toLowerCase() === 'ok' ? 'ok' : 'issue';
    }
  }
  if (isTwilio(provider) && typeof statusObj?.twilio === 'string') {
    return statusObj.twilio.toLowerCase() === 'ok' ? 'ok' : 'issue';
  }
  return 'ok';
};
const deriveEnvFromFields = (provider, providerValues = {}) => {
  const out = {};
  const base = (provider?.id || provider?.name || provider?.title || 'PROVIDER')
    .toString()
    .toUpperCase()
    .replace(/\W+/g, '_');
  (provider?.fields || []).forEach((field) => {
    const envKey = (field?.env || field?.envKey || `${base}_${String(field?.key || field?.name || '')}`)
      .toUpperCase()
      .replace(/\W+/g, '_');
    out[envKey] = providerValues?.[field?.key] ?? '';
  });
  return out;
};

const cloneProviders = (data) => JSON.parse(JSON.stringify(data || {}));

const emailFields = [
  {
    key: 'enabled',
    label: 'Enable email notifications',
    type: 'switch',
    helperText: 'Toggle SMTP email delivery for alerts.',
    env: 'SMTP_ENABLED'
  },
  {
    key: 'server',
    label: 'SMTP server',
    placeholder: 'smtp.gmail.com',
    env: 'SMTP_SERVER'
  },
  {
    key: 'port',
    label: 'Port',
    type: 'number',
    placeholder: '587',
    env: 'SMTP_PORT'
  },
  {
    key: 'username',
    label: 'Username',
    placeholder: 'alerts@example.com',
    env: 'SMTP_USERNAME'
  },
  {
    key: 'password',
    label: 'Password',
    placeholder: '••••••••',
    env: 'SMTP_PASSWORD'
  },
  {
    key: 'default_recipient',
    label: 'Default recipient',
    placeholder: 'team@example.com',
    fullWidth: true,
    env: 'SMTP_DEFAULT_RECIPIENT'
  }
];

const twilioFields = [
  {
    key: 'enabled',
    label: 'Enable Twilio voice/SMS',
    type: 'switch',
    helperText: 'Uses Twilio Programmable Voice for automated calls and texts.',
    env: 'TWILIO_ENABLED'
  },
  {
    key: 'account_sid',
    label: 'Account SID',
    placeholder: 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    env: 'TWILIO_ACCOUNT_SID'
  },
  {
    key: 'auth_token',
    label: 'Auth token',
    placeholder: '••••••••',
    env: 'TWILIO_AUTH_TOKEN'
  },
  {
    key: 'default_from_phone',
    label: 'From phone number',
    placeholder: '+15555551234',
    env: 'TWILIO_DEFAULT_FROM_PHONE'
  },
  {
    key: 'default_to_phone',
    label: 'Default recipient phone',
    placeholder: '+15555559876',
    env: 'TWILIO_DEFAULT_TO_PHONE'
  }
];

const ttsFields = [
  {
    key: 'enabled',
    label: 'Enable text-to-speech',
    type: 'switch',
    helperText: 'Requires the optional pyttsx3 dependency.',
    env: 'TTS_ENABLED'
  },
  {
    key: 'voice',
    label: 'Voice',
    placeholder: 'Hazel',
    env: 'TTS_VOICE'
  },
  {
    key: 'speed',
    label: 'Speech rate (wpm)',
    type: 'number',
    placeholder: '140',
    env: 'TTS_SPEED'
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
  const { data: resolved } = useProvidersResolved();
  const saveProviders = useSaveProviders();
  const queryClient = useQueryClient();
  const {
    data: status,
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus,
    dataUpdatedAt: statusUpdatedAt
  } = useStatus();
  const { mutate: runHeartbeat, isLoading: heartbeatRunning } = useRunHeartbeat();
  const testMsg = useTestMessage();

  const [draft, setDraft] = useState({});
  const [cooldown, setCooldownLocal] = useState(0);
  const [cooldownSaving, setCooldownSaving] = useState(false);
  const [cooldownResetting, setCooldownResetting] = useState(false);
  const [lastTwilioSid, setLastTwilioSid] = useState(null);

  const providerData = useMemo(() => {
    if (providers && typeof providers === 'object' && '__root__' in providers) {
      return providers.__root__ || {};
    }
    return providers || {};
  }, [providers]);

  const resolvedProviders = useMemo(() => {
    if (resolved && typeof resolved === 'object' && '__root__' in resolved) {
      return resolved.__root__ || {};
    }
    return resolved || {};
  }, [resolved]);

  useEffect(() => {
    if (providerData) {
      setDraft(cloneProviders(providerData));
      setCooldownLocal(providerData?.system?.phone_relax_period ?? 0);
    }
  }, [providerData]);

  useEffect(() => {
    refetchStatus?.();
  }, [refetchStatus]);

  const serializedProviders = useMemo(() => JSON.stringify(providerData || {}), [providerData]);
  const serializedDraft = useMemo(() => JSON.stringify(draft || {}), [draft]);
  const isDirty = serializedProviders !== serializedDraft;

  const invalidateProviderQueries = () => {
    queryClient.invalidateQueries({ queryKey: ['xcom', 'providers'] });
    queryClient.invalidateQueries({ queryKey: ['xcom', 'providers_resolved'] });
  };

  const onSaveCooldown = async () => {
    setCooldownSaving(true);
    try {
      const seconds = Number(cooldown || 0);
      const result = await setCooldownApi(seconds);
      if (typeof result?.seconds === 'number') {
        setCooldownLocal(result.seconds);
      }
      invalidateProviderQueries();
      enqueueSnackbar('Call cool-down updated', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar(`Unable to update cool-down: ${error?.message || error}`, { variant: 'error' });
    } finally {
      setCooldownSaving(false);
    }
  };

  const onResetCooldown = async () => {
    setCooldownResetting(true);
    try {
      await resetCooldown();
      setCooldownLocal(0);
      invalidateProviderQueries();
      enqueueSnackbar('Call cool-down reset', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar(`Unable to reset cool-down: ${error?.message || error}`, { variant: 'error' });
    } finally {
      setCooldownResetting(false);
    }
  };

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
    setDraft(cloneProviders(providerData || {}));
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

  const testFromUI = (mode) => {
    const normalized = (mode || '').toString().toLowerCase();
    const level = normalized === 'voice' ? 'HIGH' : normalized === 'sms' ? 'MEDIUM' : 'LOW';
    const payload = {
      mode: normalized,
      level,
      subject: `Test ${normalized}`,
      body: normalized === 'voice' ? 'Sonic test voice' : 'Sonic test',
      ignore_cooldown: normalized === 'voice'
    };
    testMsg.mutate(payload, {
      onSuccess: (res) => {
        const sid = res?.results?.twilio_sid;
        const toNumber = res?.results?.to_number;
        const fromNumber = res?.results?.from_number;
        const ok = !!res?.success && (normalized !== 'voice' || res?.results?.voice === true);
        if (normalized === 'voice') {
          setLastTwilioSid(sid || null);
        }
        enqueueSnackbar(
          `Test ${normalized}: ${ok ? 'ok' : 'error'}${sid ? ' · SID ' + sid : ''}${
            toNumber ? ' · to ' + toNumber : ''
          }${fromNumber ? ' · from ' + fromNumber : ''}`,
          {
            variant: ok ? 'success' : 'error'
          }
        );
      },
      onError: (err) => {
        enqueueSnackbar('Test failed: ' + (err?.message || 'unknown'), { variant: 'error' });
      }
    });
  };

  const statusEntries = useMemo(() => Object.entries(status || {}), [status]);
  const lastChecked = statusUpdatedAt ? new Date(statusUpdatedAt).toLocaleString() : null;
  const twilioSidHref = lastTwilioSid ? `${TWILIO_CALL_LOG_URL}/${lastTwilioSid}` : null;

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

    const toNumber = resolvedProviders?.twilio?.default_to_phone ?? resolvedProviders?.api?.default_to_phone ?? '';
    const fromNumber =
      resolvedProviders?.twilio?.default_from_phone ?? resolvedProviders?.api?.default_from_phone ?? '';

    const providerDefinitions = [
      {
        id: 'twilio',
        name: 'twilio',
        key: 'twilio',
        title: 'Twilio',
        description: 'Configure Twilio credentials used for automated calls and SMS.',
        fields: twilioFields,
        values: createTwilioValues(draft),
        onChange: handleTwilioChange,
        icon: '/images/twilio.png',
        externalLink: TWILIO_CONSOLE_URL,
        defaultExpanded: true,
        source: providerData?.twilio ?? providerData?.api,
        env: {
          TWILIO_ACCOUNT_SID: pick(
            resolvedProviders?.twilio?.account_sid,
            resolvedProviders?.api?.account_sid
          ),
          TWILIO_AUTH_TOKEN: pick(
            resolvedProviders?.twilio?.auth_token,
            resolvedProviders?.api?.auth_token
          ),
          TWILIO_FROM_PHONE: pick(
            resolvedProviders?.twilio?.default_from_phone,
            resolvedProviders?.twilio?.from_phone,
            resolvedProviders?.api?.default_from_phone,
            resolvedProviders?.api?.from_phone
          ),
          TWILIO_TO_PHONE: pick(
            resolvedProviders?.twilio?.default_to_phone,
            resolvedProviders?.twilio?.to_phone,
            resolvedProviders?.api?.default_to_phone,
            resolvedProviders?.api?.to_phone
          )
        },
        warnings: [
          !isE164(toNumber) && 'Default recipient must be E.164 (e.g. +16199804758).',
          !isE164(fromNumber) && 'From phone must be E.164 (e.g. +18336913467).'
        ].filter(Boolean)
      },
      {
        id: 'email',
        name: 'smtp',
        key: 'smtp',
        title: 'Email (SMTP)',
        description: 'XCom uses SMTP to deliver email alerts.',
        fields: emailFields,
        values: createEmailValues(draft),
        onChange: handleEmailChange,
        source: providerData?.email ?? providerData?.smtp,
        env: {
          SMTP_SERVER: resolvedProviders?.email?.smtp?.server ?? '',
          SMTP_PORT: resolvedProviders?.email?.smtp?.port ?? '',
          SMTP_USERNAME: resolvedProviders?.email?.smtp?.username ?? '',
          SMTP_PASSWORD: resolvedProviders?.email?.smtp?.password ?? '',
          SMTP_DEFAULT_RECIPIENT: resolvedProviders?.email?.smtp?.default_recipient ?? ''
        }
      },
      {
        id: 'sound',
        name: 'tts',
        key: 'sound',
        title: 'Text-to-Speech',
        description: 'Optional local speech synthesis for audible alerts.',
        fields: ttsFields,
        values: createTTSValues(draft),
        onChange: handleTTSChange,
        source: providerData?.tts ?? providerData?.sound
      }
    ];

    return (
      <Stack spacing={1.5}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1.5}
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1.5 }}
        >
          <TextField
            label="Call cool-down (sec)"
            type="number"
            size="small"
            value={cooldown}
            onChange={(event) => setCooldownLocal(event.target.value)}
            sx={{ width: { xs: '100%', sm: 200 } }}
            inputProps={{ min: 0 }}
          />

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} width={{ xs: '100%', sm: 'auto' }}>
            <Button
              variant="outlined"
              onClick={onSaveCooldown}
              disabled={cooldownSaving}
            >
              {cooldownSaving ? <CircularProgress size={20} /> : 'Save'}
            </Button>
            <Button
              variant="outlined"
              onClick={onResetCooldown}
              disabled={cooldownResetting}
            >
              {cooldownResetting ? <CircularProgress size={20} /> : 'Reset Cool-down'}
            </Button>
          </Stack>
        </Stack>

        {providerDefinitions
          .slice()
          .sort(sortTwilioFirst)
          .map((provider) => {
            const envMap =
              provider?.env && typeof provider.env === 'object' && provider.env !== null
                ? provider.env
                : provider?.source && typeof provider.source.env === 'object' && provider.source.env !== null
                  ? provider.source.env
                  : deriveEnvFromFields(provider, provider.values);
            return (
              <ProviderAccordion
                key={provider.id || provider.title}
                title={provider.title}
                description={provider.description}
                fields={provider.fields}
                values={provider.values}
                onChange={provider.onChange}
                icon={provider.icon}
                externalLink={provider.externalLink}
                defaultExpanded={Boolean(provider.defaultExpanded)}
                status={resolveStatus(status, provider)}
                env={envMap}
                warnings={provider.warnings}
              />
            );
          })}
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
      <Grid item xs={12}>
        <Card sx={{ mb: 3 }}>
          <CardHeader title="Operations" />
          <CardContent>
            <Stack direction="row" spacing={1.5} useFlexGap flexWrap="wrap" sx={{ mb: 1 }}>
              <Button
                component="a"
                href={TWILIO_CONSOLE_URL}
                target="_blank"
                rel="noopener noreferrer"
                variant="contained"
                color="inherit"
                size="large"
                sx={{ fontWeight: 900, px: 2.25, py: 1.1 }}
                startIcon={<TwilioIcon />}
                endIcon={<IconExternalLink size={18} />}
              >
                Twilio Console
              </Button>
              <Button
                variant="contained"
                startIcon={<IconPhone size={18} />}
                onClick={() => testFromUI('voice')}
                disabled={testMsg.isLoading}
              >
                Test Voice
              </Button>
              <Button
                variant="outlined"
                startIcon={<IconMail size={18} />}
                onClick={() => testFromUI('email')}
                disabled={testMsg.isLoading}
              >
                Test Email
              </Button>
              <Button
                variant="outlined"
                startIcon={<IconVolume2 size={18} />}
                onClick={() => testFromUI('sound')}
                disabled={testMsg.isLoading}
              >
                Test Sound
              </Button>
              <Button
                variant="contained"
                color="secondary"
                startIcon={<IconActivity size={18} />}
                onClick={() =>
                  runHeartbeat(undefined, {
                    onSuccess: () => enqueueSnackbar('XCom heartbeat completed', { variant: 'success' }),
                    onError: (e) => enqueueSnackbar('Heartbeat failed: ' + (e?.message || 'unknown'), {
                      variant: 'error'
                    })
                  })
                }
                disabled={heartbeatRunning}
              >
                {heartbeatRunning ? <CircularProgress size={20} color="inherit" /> : 'Run Heartbeat Now'}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
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

              {lastTwilioSid ? (
                <Typography variant="caption" color="text.secondary">
                  Last Twilio SID:{' '}
                  {twilioSidHref ? (
                    <a href={twilioSidHref} target="_blank" rel="noopener noreferrer">
                      {lastTwilioSid}
                    </a>
                  ) : (
                    lastTwilioSid
                  )}
                </Typography>
              ) : null}
            </Stack>
          </MainCard>
        </Stack>
      </Grid>
    </Grid>
  );
}
