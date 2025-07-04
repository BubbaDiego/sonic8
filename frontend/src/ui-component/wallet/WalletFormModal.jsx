import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, TextField, Checkbox, FormControlLabel, MenuItem } from '@mui/material';
import { useFormik } from 'formik';
import * as Yup from 'yup';

const schema = Yup.object().shape({
  name: Yup.string().required('Required'),
  public_address: Yup.string().required('Required'),
  balance: Yup.number().min(0, 'Must be positive')
});

const WalletFormModal = ({ open, mode, initialValues, onSubmit, onClose }) => {
  const formik = useFormik({
    enableReinitialize: true,
    initialValues,
    validationSchema: schema,
    onSubmit: (values) => {
      onSubmit(values);
      onClose();
    }
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{mode === 'add' ? '➕ Add Wallet' : '✏️ Edit Wallet'}</DialogTitle>
      <form onSubmit={formik.handleSubmit}>
        <DialogContent dividers>
          <TextField
            margin="dense"
            fullWidth
            label="Name"
            name="name"
            value={formik.values.name}
            onChange={formik.handleChange}
            error={formik.touched.name && Boolean(formik.errors.name)}
            helperText={formik.touched.name && formik.errors.name}
          />
          <TextField
            margin="dense"
            fullWidth
            label="Public Address"
            name="public_address"
            value={formik.values.public_address}
            onChange={formik.handleChange}
            error={formik.touched.public_address && Boolean(formik.errors.public_address)}
            helperText={formik.touched.public_address && formik.errors.public_address}
          />
          <TextField
            margin="dense"
            fullWidth
            label="Image Path"
            name="image_path"
            value={formik.values.image_path}
            onChange={formik.handleChange}
          />
          <TextField
            margin="dense"
            fullWidth
            label="Balance (USD)"
            name="balance"
            type="number"
            value={formik.values.balance}
            onChange={formik.handleChange}
            error={formik.touched.balance && Boolean(formik.errors.balance)}
            helperText={formik.touched.balance && formik.errors.balance}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={formik.values.is_active}
                name="is_active"
                onChange={formik.handleChange}
              />
            }
            label="Active"
          />
          <TextField
            margin="dense"
            select
            label="Type"
            name="type"
            value={formik.values.type}
            onChange={formik.handleChange}
            fullWidth
          >
            {['personal', 'bot', 'exchange', 'test'].map((opt) => (
              <MenuItem key={opt} value={opt}>{opt}</MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained">Save</Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default WalletFormModal;
