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

/* ------------------------------------------------------------------ */
/* 💅🏼  PUBLIC STYLE CONFIGS – edit these four values and go          */
/* ------------------------------------------------------------------ */
const TITLE_AREA_HEIGHT = 40;               // px: height of the blue header bar
const TITLE_FONT_FAMILY = 'Roboto, sans-serif';
const TITLE_FONT_SIZE = 22;                 // px
const TRADER_ROW_HEIGHT = 35;               // px: height of each trader row
/* ------------------------------------------------------------------ */
// If you ever want avatar size or other quirks exposed the same way,
// just add more constants above. 🙂
// --------------------------------------------------------------------

// (Kept as a constant so it isn’t accidentally overridden by props)
const CARD_TITLE_TEXT = 'Traders';

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
      // Override the default MUI CardHeader to respect our height
      sx={{
        '& .MuiCardHeader-root': { minHeight: TITLE_AREA_HEIGHT, p: 0 },
        '& .MuiCardHeader-content': { m: 0 }
      }}
      title={
        <Typography
          sx={{
            fontFamily: TITLE_FONT_FAMILY,
            fontSize: TITLE_FONT_SIZE,
            lineHeight: `${TITLE_AREA_HEIGHT}px`, // vertical centering
            fontWeight: 600
          }}
        >
          {CARD_TITLE_TEXT}
        </Typography>
      }
      content={false}
    >
      {/* Fixed body height so the list scrolls beneath the header */}
      <Box sx={{ height: 370, overflowY: 'auto' }}>
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
                      <Typography variant="subtitle1">
                        {trader.name}
                      </Typography>

                      <Typography variant="subtitle2" fontWeight={500}>
                        ${Number(trader.wallet_balance).toLocaleString()}
                      </Typography>

                      <Typography
                        variant="subtitle2"
                        sx={{
                          color:
                            trader.profit >= 0 ? 'success.dark' : 'error.main'
                        }}
                      >
                        {trader.profit >= 0 ? '+' : '-'}$
                        {Math.abs(trader.profit).toLocaleString()}
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
