
// TraderListCard.jsx
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
import PerfectScrollbar from 'react-perfect-scrollbar';
import MainCard from 'ui-component/cards/MainCard';

// Stubbed API call
const fetchTraders = async () => {
  // Replace this with real API call later
  return Promise.resolve([
    {
      id: 1,
      name: 'Trader Joe',
      image: '/static/images/avatar1.png',
      balance: '$25,340',
      pnl: '+$3,200',
      pnlColor: 'success.dark'
    },
    {
      id: 2,
      name: 'Jane Doe',
      image: '/static/images/avatar2.png',
      balance: '$17,920',
      pnl: '-$1,050',
      pnlColor: 'error.main'
    },
    {
      id: 3,
      name: 'Alpha Trader',
      image: '/static/images/avatar3.png',
      balance: '$45,100',
      pnl: '+$8,560',
      pnlColor: 'success.dark'
    }
  ]);
};

export default function TraderListCard({ title }) {
  const [traders, setTraders] = useState([]);

  useEffect(() => {
    const loadData = async () => {
      const data = await fetchTraders();
      setTraders(data);
    };

    loadData();
  }, []);

  return (
    <MainCard title={title} content={false}>
      <PerfectScrollbar style={{ height: 370 }}>
        <List>
          {traders.map((trader) => (
            <div key={trader.id}>
              <ListItemButton>
                <ListItemAvatar>
                  <Avatar src={trader.image} alt={trader.name} />
                </ListItemAvatar>
                <ListItemText
                  primary={
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography variant="subtitle1">{trader.name}</Typography>
                      <Typography variant="subtitle2" sx={{ fontWeight: 500 }}>
                        {trader.balance}
                      </Typography>
                      <Typography variant="subtitle2" sx={{ color: trader.pnlColor }}>
                        {trader.pnl}
                      </Typography>
                    </Stack>
                  }
                />
              </ListItemButton>
              <Divider />
            </div>
          ))}
        </List>
      </PerfectScrollbar>
    </MainCard>
  );
}

TraderListCard.propTypes = { title: PropTypes.string };
