import PropTypes from 'prop-types';
import { useState, useMemo } from 'react';
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
  actions
}) => {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const normalizedValues = useMemo(() => values || {}, [values]);

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
    <Accordion expanded={expanded} onChange={(_, isExpanded) => setExpanded(isExpanded)} sx={{ mb: 2 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <Typography variant="h5">{title}</Typography>
          {description && (
            <Typography variant="body2" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>
      </AccordionSummary>
      <AccordionDetails>
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
                  {helperText && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.25 }}>
                      {helperText}
                    </Typography>
                  )}
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
  actions: PropTypes.node
};

export default ProviderAccordion;
