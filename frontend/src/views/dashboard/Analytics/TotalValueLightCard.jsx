import PropTypes from 'prop-types';
import { useEffect, useState } from 'react';
import { styled, useTheme, alpha } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import MainCard from 'ui-component/cards/MainCard';
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined';
import { ThemeMode } from 'config';

const CardWrapper = styled(MainCard)(({ theme }) => ({
  overflow: 'hidden',
  position: 'relative',
  '&:after': {
    content: '""',
    position: 'absolute',
    width: 210,
    height: 210,
    background: `linear-gradient(210.04deg, ${theme.palette.warning.dark} -50.94%, rgba(144, 202, 249, 0) 83.49%)`,
    borderRadius: '50%',
    top: -30,
    right: -180
  },
  '&:before': {
    content: '""',
    position: 'absolute',
    width: 210,
    height: 210,
    background: `linear-gradient(140.9deg, ${theme.palette.warning.dark} -14.02%, rgba(144, 202, 249, 0) 70.50%)`,
    borderRadius: '50%',
    top: -160,
    right: -130
  }
}));

export default function TotalValueLightCard({ isLoading, value, label = 'Total Value' }) {
  const theme = useTheme();
  const [totalValue, setTotalValue] = useState('0');

  useEffect(() => {
    if (value !== undefined && value !== null) {
      setTotalValue(Math.round(value).toLocaleString());
      return;
    }
  }, [value]);

  return (
    <CardWrapper border={false} content={false}>
      <Box sx={{ p: 2 }}>
        <List sx={{ py: 0 }}>
          <ListItem alignItems="center" disableGutters sx={{ py: 0 }}>
            <ListItemAvatar>
              <Avatar
                variant="rounded"
                sx={{
                  ...theme.typography.commonAvatar,
                  ...theme.typography.largeAvatar,
                  bgcolor:
                    theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'warning.light',
                  color: 'warning.dark'
                }}
              >
                <TableChartOutlinedIcon fontSize="inherit" />
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              sx={{ py: 0, mt: 0.45, mb: 0.45 }}
              primary={
                <Typography variant="h4">
                  {totalValue}
                </Typography>
              }
              secondary={
                <Typography variant="subtitle2" sx={{ color: 'grey.500', mt: 0.5 }}>
                  {label}
                </Typography>
              }
            />
          </ListItem>
        </List>
      </Box>
    </CardWrapper>
  );
}

TotalValueLightCard.propTypes = {
  isLoading: PropTypes.bool,
  value: PropTypes.number,
  label: PropTypes.string
};
