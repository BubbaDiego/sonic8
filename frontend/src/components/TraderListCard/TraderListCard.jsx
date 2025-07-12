import { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import Divider from '@mui/material/Divider';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import Avatar from '@mui/material/Avatar';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import MainCard from 'ui-component/cards/MainCard';
import { getTraders } from 'api/traders';

/**
 * Adjustable height for each individual trader row.
 * Modify this value to increase or decrease the trader row height.
 */
const TRADER_ROW_HEIGHT = 50;

/**
 * Adjustable size (in px) for the trader avatars/icons.
 * Modify this to increase or decrease the size of the trader icons.
 */
const TRADER_ICON_SIZE = 30;

export default function TraderListCard({ title }) {
  const [traders, setTraders] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await getTraders();
        setTraders(data);
      } catch (error) {
        console.error('Error fetching traders:', error);
      }
    };

    loadData();
  }, []);

  return (
    <MainCard title={title} content={false}>
      <Box sx={{ height: 370, overflowY: 'auto' }}>
        <List>
          {traders.map((trader) => (
            <div key={trader.name}>
              <ListItemButton sx={{ height: TRADER_ROW_HEIGHT }}>
                <ListItemAvatar>
                  <Avatar
                    src={trader.avatar}
                    alt={trader.name}
                    sx={{ width: TRADER_ICON_SIZE, height: TRADER_ICON_SIZE }}
                  />
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography variant="subtitle1">{trader.name}</Typography>
                      <Typography variant="subtitle2" sx={{ fontWeight: 500 }}>
                        ${Number(trader.wallet_balance).toLocaleString()}
                      </Typography>
                      <Typography
                        variant="subtitle2"
                        sx={{ color: trader.profit >= 0 ? 'success.dark' : 'error.main' }}
                      >
                        {trader.profit >= 0 ? '+' : '-'}${Math.abs(trader.profit).toLocaleString()}
                      </Typography>
                    </Stack>
                  }
                />
              </ListItemButton>
              <Divider />
            </div>
          ))}
        </List>
      </Box>
    </MainCard>
  );
}

TraderListCard.propTypes = { title: PropTypes.string };
