// src/views/traderShop/TraderFormDrawer.jsx
import React from 'react';
import PropTypes from 'prop-types';
import {
  SwipeableDrawer,
  Drawer,
  Box,
  Typography,
  IconButton,
  Stack,
  Button,
  useMediaQuery
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

import { TextField, Slider } from '@mui/material';
import { updateTrader, createTrader } from './hooks';

const TraderSchema = Yup.object().shape({
  name: Yup.string().required('Required'),
  avatar: Yup.string(),
  color: Yup.string(),
  persona: Yup.string(),
  strategies: Yup.object()
});

const defaultStrategies = {
  'dynamic hedging': 33,
  'profit management': 67
};

function TraderFormDrawer({ open, onClose, initial }) {
  const isMobile = useMediaQuery((theme) => theme.breakpoints.down('sm'));
  const DrawerComponent = isMobile ? SwipeableDrawer : Drawer;
  const anchor = isMobile ? 'bottom' : 'right';

  const handleSubmit = async (values, helpers) => {
    try {
      if (initial) {
        await updateTrader(initial.name, values);
      } else {
        await createTrader(values);
      }
      onClose(true);
    } catch (e) {
      console.error(e);
      helpers.setSubmitting(false);
    }
  };

  return (
    <DrawerComponent anchor={anchor} open={open} onClose={() => onClose(false)}>
      <Box sx={{ width: isMobile ? '100%' : 420, p: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">{initial ? 'Edit Trader' : 'New Trader'}</Typography>
          <IconButton onClick={() => onClose(false)} size="large">
            <CloseIcon />
          </IconButton>
        </Stack>

        <Formik
          initialValues={{
            name: initial?.name || '',
            avatar: initial?.avatar || '',
            color: initial?.color || '',
            persona: initial?.persona || '',
            strategies: initial?.strategies || defaultStrategies
          }}
          validationSchema={TraderSchema}
          onSubmit={handleSubmit}
        >
          {({ values, isSubmitting, setFieldValue }) => (
            <Form>
              <Stack spacing={2}>
                <Field
                  as={TextField}
                  name="name"
                  label="Name"
                  fullWidth
                  disabled={!!initial}
                />
                <Field
                  as={TextField}
                  name="avatar"
                  label="Avatar URL or Emoji"
                  fullWidth
                />
                <Field as={TextField} name="color" label="Color" fullWidth />
                <Field as={TextField} name="persona" label="Persona" fullWidth />

                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    Strategy Weights
                  </Typography>
                  {Object.keys(values.strategies).map((key) => (
                    <Box key={key} sx={{ mb: 2 }}>
                      <Typography variant="caption">{key}</Typography>
                      <Slider
                        value={values.strategies[key]}
                        onChange={(_, v) => {
                          setFieldValue(`strategies.${key}`, v);
                        }}
                        valueLabelDisplay="auto"
                        step={1}
                        min={0}
                        max={100}
                      />
                    </Box>
                  ))}
                </Box>

                <Button
                  type="submit"
                  variant="contained"
                  disabled={isSubmitting}
                  fullWidth={isMobile}
                >
                  Save
                </Button>
              </Stack>
            </Form>
          )}
        </Formik>
      </Box>
    </DrawerComponent>
  );
}

TraderFormDrawer.propTypes = {
  open: PropTypes.bool,
  onClose: PropTypes.func,
  initial: PropTypes.object
};

export default TraderFormDrawer;
