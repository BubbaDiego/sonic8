import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useTheme } from '@mui/material/styles';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Avatar from "ui-component/extended/Avatar";
import { ThemeMode } from "config";
import { gridSpacing } from "store/constant";
import MoreHorizOutlinedIcon from '@mui/icons-material/MoreHorizOutlined';
import VisibilityIcon from '@mui/icons-material/Visibility';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';

export default function TraderCard({ trader, onDelete }) {
  const theme = useTheme();

  const [anchorEl, setAnchorEl] = useState(null);

  const handleMenuClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  return (
    <Card
      sx={{
        p: 2,
        bgcolor: theme.palette.mode === ThemeMode.DARK ? 'background.default' : 'grey.50',
        border: '1px solid',
        borderColor: 'divider',
        '&:hover': {
          borderColor: 'primary.main'
        }
      }}
    >
      <Grid container spacing={gridSpacing}>
        <Grid item xs={12} container justifyContent="space-between">
          <Avatar alt={trader.name} size="lg" src={trader.avatar} />
          <IconButton onClick={handleMenuClick} aria-label="more-options">
            <MoreHorizOutlinedIcon />
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
            <MenuItem onClick={handleMenuClose}>Edit</MenuItem>
            <MenuItem
              onClick={() => {
                handleMenuClose();
                onDelete(trader.name);
              }}
            >
              Delete
            </MenuItem>
          </Menu>
        </Grid>

        <Grid item xs={12}>
          <Typography variant="h5">{trader.name}</Typography>
          <Typography variant="subtitle2">{trader.persona}</Typography>
        </Grid>

        <Grid item xs={12}>
          <Typography variant="body2" sx={{ color: 'grey.700' }}>
            Mood: {trader.mood}, Heat: {trader.heat_index.toFixed(1)}
          </Typography>
        </Grid>

        <Grid item xs={12}>
          <Typography variant="caption">Profit</Typography>
          <Typography variant="h6">${trader.profit}</Typography>
        </Grid>

        <Grid item xs={12} container spacing={gridSpacing}>
          <Grid item xs={6}>
            <Typography variant="caption">Wallet Balance</Typography>
            <Typography variant="h6">${trader.wallet_balance}</Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="caption">Risk Profile</Typography>
            <Typography variant="h6">{trader.risk_profile}</Typography>
          </Grid>
        </Grid>

        <Grid item xs={12} container spacing={1}>
          <Grid item xs={6}>
            <Button variant="outlined" fullWidth startIcon={<VisibilityIcon />}>
              View
            </Button>
          </Grid>
          <Grid item xs={6}>
            <Button variant="outlined" color="primary" fullWidth startIcon={<NotificationsActiveIcon />}>
              Monitor
            </Button>
          </Grid>
        </Grid>
      </Grid>
    </Card>
  );
}

TraderCard.propTypes = {
  trader: PropTypes.object.isRequired,
  onDelete: PropTypes.func.isRequired
};
