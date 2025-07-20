import { useEffect, useState } from 'react';
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
import SentimentSatisfiedAltIcon from '@mui/icons-material/SentimentSatisfiedAlt';
import SentimentNeutralIcon from '@mui/icons-material/SentimentNeutral';
import SentimentDissatisfiedIcon from '@mui/icons-material/SentimentDissatisfied';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';            // <— NEW
import { getTraders } from 'api/traders';
import { useTheme } from '@mui/material/styles';

const TITLE_AREA_HEIGHT = 40;
const TRADER_ROW_HEIGHT = 35;
const FOOTER_HEIGHT = 36;                                            // <— NEW

const moodIcons = {
  happy: SentimentSatisfiedAltIcon,
  neutral: SentimentNeutralIcon,
  sad: SentimentDissatisfiedIcon
};

export default function TraderListCard() {
  const [traders, setTraders] = useState([]);
  const theme = useTheme();

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

  // 👉 count traders with a positive wallet balance
  const activeCount = traders.filter(
    (t) => Number(t.wallet_balance) > 0
  ).length;

  return (
    <MainCard
      sx={{
        '& .MuiCardHeader-root': { minHeight: TITLE_AREA_HEIGHT, p: 0 },
        '& .MuiCardHeader-content': { m: 0 },
        bgcolor: theme.palette.background.paper,
        color: theme.palette.text.primary
      }}
      content={false}
    >
      {/* ── Scrollable content (header + list) ───────────────────── */}
      <Box
        sx={{
          height: `calc(370px - ${FOOTER_HEIGHT}px)`,   // leave room for footer
          overflowY: 'auto'
        }}
      >
        {/* column icons header */}
        <Stack
          direction="row"
          spacing={2}
          justifyContent="space-around"
          alignItems="center"
          sx={{ p: 1, bgcolor: theme.palette.background.default }}
        >
          <AccountBalanceWalletIcon />
          <TrendingUpIcon />
          <SentimentSatisfiedAltIcon />
        </Stack>

        {/* trader rows */}
        <List disablePadding>
          {traders.map((trader) => {
            const MoodIcon = moodIcons[trader.mood] || SentimentNeutralIcon;
            return (
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
                          sx={{ color: trader.profit >= 0 ? 'success.main' : 'error.main' }}
                        >
                          {trader.profit >= 0 ? '+' : '-'}$
                          {Math.abs(trader.profit).toLocaleString()}
                        </Typography>
                        <MoodIcon sx={{ color: theme.palette.text.secondary }} />
                      </Stack>
                    }
                  />
                </ListItemButton>
                <Divider />
              </div>
            );
          })}
        </List>
      </Box>

      {/* ── Footer badge (always visible) ───────────────────────── */}
      <Stack
        direction="row"
        spacing={0.5}
        alignItems="center"
        justifyContent="center"
        sx={{
          height: FOOTER_HEIGHT,
          bgcolor: 'success.light',
          borderTop: `1px solid ${theme.palette.divider}`
        }}
      >
        <PeopleAltIcon fontSize="small" sx={{ color: 'success.dark' }} />
        <Typography
          variant="subtitle2"
          fontWeight={600}
          sx={{ color: 'success.dark' }}
        >
          {activeCount} Active
        </Typography>
      </Stack>
    </MainCard>
  );
}
