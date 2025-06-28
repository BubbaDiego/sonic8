import PropTypes from 'prop-types';
// material-ui
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

// project imports
import SubCard from 'ui-component/cards/SubCard';

// assets
import EditTwoToneIcon from '@mui/icons-material/EditTwoTone';
import DeleteTwoToneIcon from '@mui/icons-material/DeleteTwoTone';

export default function AddressCard({ address, single, change, handleClickOpen, billingAddressHandler, onBack }) {
  return (
    <SubCard sx={{ height: single ? 'auto' : '100%' }}>
      {address && (
        <Grid container spacing={2}>
          {single && (
            <Grid size={12}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Typography variant={change ? 'h3' : 'h3'}>Shipping Address</Typography>
                {change && (
                  <Button variant="contained" size="small" color="primary" startIcon={<EditTwoToneIcon />} onClick={onBack}>
                    Change
                  </Button>
                )}
              </Stack>
            </Grid>
          )}
          <Grid size={12}>
            <Stack direction="row" alignItems="center" justifyContent="space-between">
              <Stack direction="row" alignItems="center" spacing={0.5}>
                <Typography variant="subtitle1">{address.name}</Typography>
                <Typography variant="caption" sx={{ textTransform: 'capitalize' }}>
                  ({address.destination})
                </Typography>
              </Stack>
              {address.isDefault && <Chip label="Default" size="small" />}
            </Stack>
          </Grid>
          <Grid size={12}>
            <Stack spacing={0.5}>
              <Typography variant="body2">
                {`${address.building}, ${address.street}, ${address.city}, ${address.state}, ${address.country} - ${address.post}`}
              </Typography>
              <Typography variant="caption" color="secondary">
                {address.phone}
              </Typography>
            </Stack>
          </Grid>
          {!single && (
            <Grid size={12}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                {billingAddressHandler && (
                  <Button variant="outlined" onClick={() => billingAddressHandler(address)}>
                    Deliver to this Address
                  </Button>
                )}
                <Stack direction="row" alignItems="center" spacing={0}>
                  {handleClickOpen && (
                    <IconButton size="small" onClick={() => handleClickOpen(address)} aria-label="Edit Address">
                      <EditTwoToneIcon fontSize="small" />
                    </IconButton>
                  )}
                  <IconButton size="small" aria-label="Delete Address">
                    <DeleteTwoToneIcon fontSize="small" />
                  </IconButton>
                </Stack>
              </Stack>
            </Grid>
          )}
        </Grid>
      )}
    </SubCard>
  );
}

AddressCard.propTypes = {
  address: PropTypes.any,
  single: PropTypes.bool,
  change: PropTypes.bool,
  handleClickOpen: PropTypes.func,
  billingAddressHandler: PropTypes.func,
  onBack: PropTypes.func
};
