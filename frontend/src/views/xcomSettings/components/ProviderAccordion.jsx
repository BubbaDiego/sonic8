import PropTypes from 'prop-types';
import { useMemo, useState } from 'react';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TextField from '@mui/material/TextField';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import MenuItem from '@mui/material/MenuItem';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import Alert from '@mui/material/Alert';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import { IconExternalLink } from '@tabler/icons-react';

const fieldValue = (values, key) => {
  if (!values) return '';
  return typeof values[key] === 'undefined' || values[key] === null ? '' : values[key];
};

const ProviderAccordion = ({
  title,
  description,
  fields,
  values,
  onChange,
  defaultExpanded = false,
  actions,
  icon,
  externalLink,
  status,
  env = {},
  warnings = []
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [showEnv, setShowEnv] = useState(true);

  const normalizedValues = useMemo(() => values || {}, [values]);
  const envEntries = useMemo(() => Object.entries(env || {}), [env]);
  const hasEnv = envEntries.length > 0;
  const normalizedWarnings = useMemo(
    () => (Array.isArray(warnings) ? warnings.filter(Boolean) : []),
    [warnings]
  );

  const mask = (val) => {
    if (val === null || typeof val === 'undefined') {
      return '—';
    }
    const str = String(val);
    if (str.length === 0) {
      return '—';
    }
    if (str.length <= 6) {
      return '•'.repeat(Math.max(2, str.length || 2));
    }
    const maskedLength = Math.max(2, str.length - 6);
    return `${str.slice(0, 2)}${'•'.repeat(maskedLength)}${str.slice(-4)}`;
  };

  const handleFieldChange = (key, rawValue, field) => {
    const next = { ...normalizedValues };
    if (field?.type === 'number') {
      next[key] = rawValue === '' ? '' : Number(rawValue);
    } else {
      next[key] = rawValue;
    }
    onChange?.(next);
  };

  const handleToggle = (key, checked) => {
    const next = { ...normalizedValues, [key]: checked };
    onChange?.(next);
  };

  return (
    <Accordion
      expanded={expanded}
      onChange={(_, isExpanded) => setExpanded(isExpanded)}
      disableGutters
      sx={{
        mb: 2,
        borderLeft: '4px solid',
        borderColor: status === 'ok' ? 'success.main' : status === 'issue' ? 'error.main' : 'divider'
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, width: '100%' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
              {icon ? (
                <Box
                  component="img"
                  src={icon}
                  alt={`${title} icon`}
                  onError={(event) => {
                    event.currentTarget.onerror = null;
                    event.currentTarget.src = '/static/images/twilio.png';
                  }}
                  sx={{ height: 20, width: 20, borderRadius: '4px' }}
                />
              ) : null}
              <Typography variant="h5" noWrap>
                {title}
              </Typography>
              {typeof status === 'string' ? (
                <Chip
                  size="small"
                  label={status === 'ok' ? 'OK' : 'ISSUE'}
                  color={status === 'ok' ? 'success' : 'error'}
                  variant="filled"
                  sx={{ ml: 0.5 }}
                />
              ) : null}
            </Box>

            {externalLink ? (
              <Tooltip title="Open Console">
                <IconButton size="small" component="a" href={externalLink} target="_blank" rel="noopener noreferrer">
                  <IconExternalLink size={18} />
                </IconButton>
              </Tooltip>
            ) : null}
          </Box>
          {description ? (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          ) : null}
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {normalizedWarnings.length > 0 ? (
          <Box sx={{ mb: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
            {normalizedWarnings.map((warning, index) => (
              <Alert severity="warning" key={index} sx={{ py: 0.75 }}>
                {warning}
              </Alert>
            ))}
          </Box>
        ) : null}

        {hasEnv ? (
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                Environment
              </Typography>
              <Tooltip title={showEnv ? 'Hide values' : 'Show values'}>
                <IconButton size="small" onClick={() => setShowEnv((prev) => !prev)}>
                  {showEnv ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                </IconButton>
              </Tooltip>
            </Box>
            <Grid container spacing={1}>
              {envEntries.map(([envKey, envValue]) => (
                <Grid item xs={12} md={6} key={envKey}>
                  <Typography variant="caption" sx={{ opacity: 0.7 }}>
                    {envKey}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis'
                    }}
                  >
                    {showEnv ? mask(envValue) : '••••••••••'}
                  </Typography>
                </Grid>
              ))}
            </Grid>
          </Box>
        ) : null}

        {hasEnv ? <Divider sx={{ mb: 2 }} /> : null}

        <Grid container spacing={2}>
          {fields.map((field) => {
            const {
              key,
              label,
              helperText,
              type = 'text',
              placeholder,
              fullWidth = false,
              options
            } = field;
            const gridSize = fullWidth ? 12 : 6;

            if (type === 'switch') {
              return (
                <Grid item xs={12} key={key}>
                  <FormControlLabel
                    control={
                      <Switch
                        color="primary"
                        checked={Boolean(fieldValue(normalizedValues, key))}
                        onChange={(event) => handleToggle(key, event.target.checked)}
                      />
                    }
                    label={label}
                  />
                  {helperText ? (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                      {helperText}
                    </Typography>
                  ) : null}
                </Grid>
              );
            }

            return (
              <Grid item xs={12} md={gridSize} key={key}>
                <TextField
                  fullWidth
                  label={label}
                  type={type === 'number' ? 'number' : 'text'}
                  placeholder={placeholder}
                  helperText={helperText}
                  value={fieldValue(normalizedValues, key)}
                  onChange={(event) => handleFieldChange(key, event.target.value, field)}
                  InputLabelProps={type === 'number' ? { shrink: true } : undefined}
                  select={Array.isArray(options) && options.length > 0}
                >
                  {Array.isArray(options) && options.length > 0
                    ? options.map((option) => (
                        <MenuItem key={option.value ?? option} value={option.value ?? option}>
                          {option.label ?? option}
                        </MenuItem>
                      ))
                    : null}
                </TextField>
              </Grid>
            );
          })}

          {actions ? (
            <Grid item xs={12}>
              {actions}
            </Grid>
          ) : null}
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
};

ProviderAccordion.propTypes = {
  title: PropTypes.string.isRequired,
  description: PropTypes.string,
  fields: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      helperText: PropTypes.string,
      type: PropTypes.oneOf(['text', 'number', 'switch']),
      placeholder: PropTypes.string,
      fullWidth: PropTypes.bool,
      options: PropTypes.array
    })
  ).isRequired,
  values: PropTypes.object,
  onChange: PropTypes.func,
  defaultExpanded: PropTypes.bool,
  actions: PropTypes.node,
  icon: PropTypes.string,
  externalLink: PropTypes.string,
  status: PropTypes.oneOf(['ok', 'issue']),
  env: PropTypes.object,
  warnings: PropTypes.arrayOf(PropTypes.node)
};

export default ProviderAccordion;
