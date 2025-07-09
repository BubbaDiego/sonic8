import PropTypes from 'prop-types';
import { useEffect, useState } from 'react';
import { styled, useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import MainCard from 'ui-component/cards/MainCard';
import AttachMoneyOutlinedIcon from '@mui/icons-material/AttachMoneyOutlined';

const CardWrapper = styled(MainCard)(({ theme }) => ({
  backgroundColor: theme.palette.primary.dark,
  color: theme.palette.primary.light,
  overflow: 'hidden',
  position: 'relative',
  '&:after': {
    content: '""',
    position: 'absolute',
    width: 210,
    height: 210,
    background: `linear-gradient(210.04deg, ${theme.palette.primary[200]} -50.94%, rgba(144, 202, 249, 0) 83.49%)`,
    borderRadius: '50%',
    top: -30,
    right: -180
  },
  '&:before': {
    content: '""',
    position: 'absolute',
    width: 210,
    height: 210,
    background: `linear-gradient(140.9deg, ${theme.palette.primary[200]} -14.02%, rgba(144, 202, 249, 0) 77.58%)`,
    borderRadius: '50%',
    top: -160,
    right: -130
  }
}));

export default function TotalValueDarkCard({ isLoading, value }) {
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
                  bgcolor: 'primary.800',
                  color: '#fff'
                }}
              >
                <AttachMoneyOutlinedIcon fontSize="inherit" />
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              sx={{ py: 0, mt: 0.45, mb: 0.45 }}
              primary={
                <Typography variant="h4" sx={{ color: '#fff' }}>
                  {totalValue}
                </Typography>
              }
              secondary={
                <Typography variant="subtitle2" sx={{ color: 'primary.light', mt: 0.25 }}>
                  Value
                </Typography>
              }
            />
          </ListItem>
        </List>
      </Box>
    </CardWrapper>
  );
}

TotalValueDarkCard.propTypes = {
  isLoading: PropTypes.bool,
  value: PropTypes.number
};
