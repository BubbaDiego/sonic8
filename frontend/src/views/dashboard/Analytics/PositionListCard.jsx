// PositionListCard.jsx (updated to Positions data with liquidation distance and travel percent)
import { useState, useEffect, useMemo } from 'react';
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
import TableSortLabel from '@mui/material/TableSortLabel';
import PerfectScrollbar from 'react-perfect-scrollbar';
import MainCard from 'ui-component/cards/MainCard';
import axios from 'utils/axios';
import Avatar from '@mui/material/Avatar';
import Box from '@mui/material/Box';
import WaterDropTwoToneIcon from '@mui/icons-material/WaterDropTwoTone';

export default function PositionListCard({ title }) {
  const [positions, setPositions] = useState([]);
  const [orderBy, setOrderBy] = useState('wallet_name');
  const [order, setOrder] = useState('asc');

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

  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      const aVal = a[orderBy];
      const bVal = b[orderBy];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return order === 'asc' ? -1 : 1;
      if (bVal == null) return order === 'asc' ? 1 : -1;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      }
      return order === 'asc' ? (aVal < bVal ? -1 : 1) : bVal < aVal ? -1 : 1;
    });
  }, [positions, order, orderBy]);

  const handleSort = (property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  return (
    <MainCard title={title} content={false}>
      <PerfectScrollbar style={{ height: 345, padding: 0 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ pl: 3 }}>
                  <TableSortLabel
                    active={orderBy === 'wallet_name'}
                    direction={orderBy === 'wallet_name' ? order : 'asc'}
                    onClick={() => handleSort('wallet_name')}
                  >
                    Wallet
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'asset_type'}
                    direction={orderBy === 'asset_type' ? order : 'asc'}
                    onClick={() => handleSort('asset_type')}
                  >
                    Asset Type
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'position_type'}
                    direction={orderBy === 'position_type' ? order : 'asc'}
                    onClick={() => handleSort('position_type')}
                  >
                    Type
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'value'}
                    direction={orderBy === 'value' ? order : 'asc'}
                    onClick={() => handleSort('value')}
                  >
                    Value
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'liquidation_distance'}
                    direction={orderBy === 'liquidation_distance' ? order : 'asc'}
                    onClick={() => handleSort('liquidation_distance')}
                  >
                    <WaterDropTwoToneIcon
                      sx={{ color: 'primary.main', verticalAlign: 'middle', mr: 0.5 }}
                    />
                    Distance
                  </TableSortLabel>
                </TableCell>
                <TableCell align="right" sx={{ pr: 3 }}>
                  <TableSortLabel
                    active={orderBy === 'travel_percent'}
                    direction={orderBy === 'travel_percent' ? order : 'asc'}
                    onClick={() => handleSort('travel_percent')}
                  >
                    Travel Percent
                  </TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedPositions.map((position) => (
                <TableRow hover key={position.id}>
                  <TableCell sx={{ pl: 3 }}>
                    <Avatar
                      src={`/static/images/${(position.wallet_name || 'unknown')
                        .replace(/\s+/g, '')
                        .replace(/vault$/i, '')
                        .toLowerCase()}_icon.jpg`}
                      alt={position.wallet_name}
                      sx={{ width: 30, height: 30 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Avatar
                      src={`/static/images/${(position.asset_type || 'unknown').toLowerCase()}_logo.png`}
                      alt={position.asset_type}
                      sx={{ width: 24, height: 24 }}
                      onError={(e) => {
                        e.currentTarget.onerror = null;
                        e.currentTarget.src = '/static/images/unknown.png';
                      }}
                    />
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
