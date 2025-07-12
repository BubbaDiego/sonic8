import { useState, useEffect, useMemo } from 'react';
import PropTypes from 'prop-types';
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
import WaterDropTwoToneIcon from '@mui/icons-material/WaterDropTwoTone';

/**
 * Adjustable height for each individual position row.
 * Modify this value to increase or decrease the position row height.
 */
const POSITION_ROW_HEIGHT = 11;

/**
 * Adjustable size (in px) for the wallet and asset icons.
 * Modify this value to increase or decrease the size of the icons.
 */
const POSITION_ICON_SIZE = 26;

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
                <TableCell>Asset</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Value</TableCell>
                <TableCell align="right">
                  <WaterDropTwoToneIcon sx={{ color: 'primary.main', verticalAlign: 'middle', mr: 0.5 }} />
                  Distance
                </TableCell>
                <TableCell align="right" sx={{ pr: 3 }}>Travel %</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedPositions.map((position) => (
                <TableRow hover key={position.id} sx={{ height: POSITION_ROW_HEIGHT }}>
                  <TableCell sx={{ pl: 3 }}>
                    <Avatar
                      src={`/static/images/${(position.wallet_name || 'unknown').replace(/\s+/g, '').replace(/vault$/i, '').toLowerCase()}_icon.jpg`}
                      alt={position.wallet_name}
                      sx={{ width: POSITION_ICON_SIZE, height: POSITION_ICON_SIZE }}
                    />
                  </TableCell>
                  <TableCell>
                    <Avatar
                      src={`/static/images/${(position.asset_type || 'unknown').toLowerCase()}_logo.png`}
                      alt={position.asset_type}
                      sx={{ width: POSITION_ICON_SIZE, height: POSITION_ICON_SIZE }}
                      onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = '/static/images/unknown.png'; }}
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
    </MainCard>
  );
}

PositionListCard.propTypes = { title: PropTypes.string };
