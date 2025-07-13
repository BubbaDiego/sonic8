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
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import MoodIcon from '@mui/icons-material/Mood';
import { getTraders } from 'api/traders';

/* ------------------------------------------------------------------ */
/* 💅🏼  PUBLIC STYLE CONFIGS – edit these four values and go          */
/* ------------------------------------------------------------------ */
const TITLE_AREA_HEIGHT = 40;
const TITLE_FONT_FAMILY = 'Roboto, sans-serif';
const TITLE_FONT_SIZE = 22;
const TRADER_ROW_HEIGHT = 35;
const HEADER_ICON_COLOR = '#90caf9';

export default function TraderListCard() {
  const [traders, setTraders] = useState([]);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await getTraders();
        setTraders(data);
      } catch (err) {
        console.error('Error fetching traders:', err);
      }
    }
    loadData();
  }, []);

  return (
    <MainCard
      sx={{
        '& .MuiCardHeader-root': { minHeight: TITLE_AREA_HEIGHT, p: 0 },
        '& .MuiCardHeader-content': { m: 0 },
        backgroundColor: '#1a2b41',
        color: '#ffffff'
      }}
      content={false}
    >
      <Box sx={{ height: 370, overflowY: 'auto' }}>
        <Stack direction="row" spacing={2} justifyContent="center" alignItems="center" sx={{ padding: 1, backgroundColor: '#1a2b41', color: HEADER_ICON_COLOR }}>
          <AccountBalanceWalletIcon />
          <TrendingUpIcon />
          <MoodIcon />
        </Stack>
        <List disablePadding>
          {traders.map((trader) => (
            <div key={trader.name}>
              <ListItemButton sx={{ height: TRADER_ROW_HEIGHT }}>
                <ListItemAvatar>
                  <Avatar
                    src={trader.avatar}
                    alt={trader.name}
                    sx={{ width: 30, height: 30 }}
                  />
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="center"
                      sx={{ width: '100%' }}
                    >
                      <Typography variant="subtitle2" fontWeight={500}>
                        ${Number(trader.wallet_balance).toLocaleString()}
                      </Typography>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          color: trader.profit >= 0 ? 'success.dark' : 'error.main'
                        }}
                      >
                        {trader.profit >= 0 ? '+' : '-'}${Math.abs(trader.profit).toLocaleString()}
                      </Typography>
                      <Typography variant="subtitle2">
                        {trader.mood}
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

TraderListCard.propTypes = {};
