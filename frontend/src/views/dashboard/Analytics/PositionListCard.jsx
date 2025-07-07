// PositionListCard.jsx (updated to Positions data with liquidation distance and travel percent)
import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import Button from '@mui/material/Button';
import CardActions from '@mui/material/CardActions';
import Divider from '@mui/material/Divider';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import PerfectScrollbar from 'react-perfect-scrollbar';
import MainCard from 'ui-component/cards/MainCard';
import axios from 'utils/axios';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';

export default function PositionListCard({ title }) {
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    async function loadPositions() {
      try {
        const response = await axios.get('/positions/');
        setPositions(response.data || []);
      } catch (e) {
        console.error(e);
      }
    }
    loadPositions();
  }, []);

  return (
    <MainCard title={title} content={false}>
      <PerfectScrollbar style={{ height: 345, padding: 0 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ pl: 3 }}>Wallet</TableCell>
                <TableCell>Asset Type</TableCell>
                <TableCell>Position Type</TableCell>
                <TableCell align="right">Value</TableCell>
                <TableCell align="right">Liquidation Distance</TableCell>
                <TableCell align="right" sx={{ pr: 3 }}>Travel Percent</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {positions.map((position) => (
                <TableRow hover key={position.id}>
                  <TableCell sx={{ pl: 3 }}>
                    <Avatar
                      src={`/static/images/${(position.wallet_name || 'unknown').replace(/\s+/g, '').replace(/vault$/i, '').toLowerCase()}_icon.jpg`}
                      alt={position.wallet_name}
                      sx={{ width: 30, height: 30 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Avatar
                        src={`/static/images/${(position.asset_type || 'unknown').toLowerCase()}_logo.png`}
                        alt={position.asset_type}
                        sx={{ width: 24, height: 24, mr: 1 }}
                        onError={(e) => {
                          e.currentTarget.onerror = null;
                          e.currentTarget.src = '/static/images/unknown.png';
                        }}
                      />
                      {position.asset_type}
                    </Box>
                  </TableCell>
                  <TableCell>{position.position_type}</TableCell>
                  <TableCell align="right">${Number(position.value || 0).toLocaleString()}</TableCell>
                  <TableCell align="right">{position.liquidation_distance}</TableCell>
                  <TableCell align="right" sx={{ pr: 3 }}>
                    {`${Number(position.travel_percent || 0).toFixed(2)}%`}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </PerfectScrollbar>

      <Divider />
      <CardActions sx={{ justifyContent: 'flex-end' }}>
        <Button variant="text" size="small">
          View all Positions
        </Button>
      </CardActions>
    </MainCard>
  );
}

PositionListCard.propTypes = { title: PropTypes.string };
