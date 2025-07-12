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
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import AccountBalanceWalletTwoToneIcon from '@mui/icons-material/AccountBalanceWalletTwoTone';
import BuildTwoToneIcon from '@mui/icons-material/BuildTwoTone';
import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import WaterDropTwoToneIcon from '@mui/icons-material/WaterDropTwoTone';
import PercentTwoToneIcon from '@mui/icons-material/PercentTwoTone';

/* --- Configurable Variables --- */
const HEADER_ROW_HEIGHT = 20;      // Height of the header row with icons (px)
const POSITION_ROW_HEIGHT = 18;    // Height of each position row (px)
const TABLE_MAX_HEIGHT = 30045;      // Maximum height of the whole table/card (px)
/* ------------------------------ */

const POSITION_ICON_SIZE = 26;

export default function PositionListCard({ title }) {
  const [positions, setPositions] = useState([]);
  const [orderBy, setOrderBy] = useState('wallet_name');
  const [order, setOrder] = useState('asc');

  useEffect(() => {
    (async () => {
      try {
        const res = await axios.get('/positions/');
        setPositions(res.data || []);
      } catch (e) {
        console.error(e);
      }
    })();
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

  const handleSort = (prop) => {
    const isAsc = orderBy === prop && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(prop);
  };

  return (
    <MainCard title={title} content={false}>
      <PerfectScrollbar style={{ height: TABLE_MAX_HEIGHT, padding: 0 }}>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ height: HEADER_ROW_HEIGHT }}>
                <TableCell sx={{ pl: 3 }}>
                  <TableSortLabel
                    active={orderBy === 'wallet_name'}
                    direction={orderBy === 'wallet_name' ? order : 'asc'}
                    onClick={() => handleSort('wallet_name')}
                  >
                    <AccountBalanceWalletTwoToneIcon color="primary" />
                  </TableSortLabel>
                </TableCell>

                <TableCell />

                <TableCell align="right">
                  <TableSortLabel
                    active={orderBy === 'leverage'}
                    direction={orderBy === 'leverage' ? order : 'asc'}
                    onClick={() => handleSort('leverage')}
                  >
                    <BuildTwoToneIcon color="primary" />
                  </TableSortLabel>
                </TableCell>

                <TableCell align="right">
                  <MonetizationOnTwoToneIcon color="primary" />
                </TableCell>
                <TableCell align="right">
                  <WaterDropTwoToneIcon color="primary" />
                </TableCell>
                <TableCell align="right" sx={{ pr: 3 }}>
                  <PercentTwoToneIcon color="primary" />
                </TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {sortedPositions.map((pos) => (
                <TableRow hover key={pos.id} sx={{ height: POSITION_ROW_HEIGHT }}>
                  <TableCell sx={{ pl: 3 }}>
                    <Avatar
                      src={`/static/images/${(pos.wallet_name || 'unknown').replace(/\s+/g, '').replace(/vault$/i, '').toLowerCase()}_icon.jpg`}
                      alt={pos.wallet_name}
                      sx={{ width: POSITION_ICON_SIZE, height: POSITION_ICON_SIZE }}
                    />
                  </TableCell>

                  <TableCell>
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <Avatar
                        src={`/static/images/${(pos.asset_type || 'unknown').toLowerCase()}_logo.png`}
                        alt={pos.asset_type}
                        sx={{ width: POSITION_ICON_SIZE, height: POSITION_ICON_SIZE }}
                        onError={(e) => {
                          e.currentTarget.onerror = null;
                          e.currentTarget.src = '/static/images/unknown.png';
                        }}
                      />
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        {pos.position_type?.toUpperCase()}
                      </Typography>
                    </Stack>
                  </TableCell>

                  <TableCell align="right">{Number(pos.leverage || 0).toFixed(2)}</TableCell>
                  <TableCell align="right">${Number(pos.value || 0).toLocaleString()}</TableCell>
                  <TableCell align="right">{pos.liquidation_distance}</TableCell>
                  <TableCell align="right" sx={{ pr: 3 }}>
                    {`${Number(pos.travel_percent || 0).toFixed(2)}%`}
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
