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
import TrendingUpTwoToneIcon from '@mui/icons-material/TrendingUpTwoTone';   // Profit
import BuildTwoToneIcon from '@mui/icons-material/BuildTwoTone';            // Leverage
import MonetizationOnTwoToneIcon from '@mui/icons-material/MonetizationOnTwoTone';
import WaterDropTwoToneIcon from '@mui/icons-material/WaterDropTwoTone';
import PercentTwoToneIcon from '@mui/icons-material/PercentTwoTone';

/* --- Configurable Variables --- */
const HEADER_ROW_HEIGHT = 20;   // Height of the header row with icons (px)
const POSITION_ROW_HEIGHT = 28; // Height of each position row (px)
const TABLE_MAX_HEIGHT = 270;   // Maximum height of the whole table/card (px)

/**
 * Any profit **strictly greater** than this value (in USD)
 * is rendered in green and bold.
 */
const profit_mark = 5;
/* ------------------------------ */

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

  // Centralised profit helper
  const calcProfit = (p) =>
    p.pnl_after_fees_usd != null
      ? Number(p.pnl_after_fees_usd)
      : p.value != null && p.collateral != null
      ? Number(p.value) - Number(p.collateral)
      : undefined;

  const sortedPositions = useMemo(() => {
    return [...positions].sort((a, b) => {
      let aVal = a[orderBy];
      let bVal = b[orderBy];

      if (orderBy === 'pnl_after_fees_usd') {
        aVal = aVal ?? calcProfit(a);
        bVal = bVal ?? calcProfit(b);
      }

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
            {/* ================= HEADER ================ */}
            <TableHead>
              <TableRow sx={{ height: HEADER_ROW_HEIGHT }}>
                {/* Wallet name */}
                <TableCell sx={{ pl: 1, py: 0.5 }}>
                  <TableSortLabel
                    active={orderBy === 'wallet_name'}
                    direction={orderBy === 'wallet_name' ? order : 'asc'}
                    onClick={() => handleSort('wallet_name')}
                  >
                    <AccountBalanceWalletTwoToneIcon color="primary" sx={{ verticalAlign: 'middle' }} />
                  </TableSortLabel>
                </TableCell>

                {/* Spacer for asset & type column */}
                <TableCell />

                {/* Profit */}
                <TableCell align="right" sx={{ py: 0.5 }}>
                  <TableSortLabel
                    active={orderBy === 'pnl_after_fees_usd'}
                    direction={orderBy === 'pnl_after_fees_usd' ? order : 'asc'}
                    onClick={() => handleSort('pnl_after_fees_usd')}
                  >
                    <TrendingUpTwoToneIcon color="primary" sx={{ verticalAlign: 'middle' }} />
                  </TableSortLabel>
                </TableCell>

                {/* Leverage */}
                <TableCell align="right" sx={{ py: 0.5 }}>
                  <TableSortLabel
                    active={orderBy === 'leverage'}
                    direction={orderBy === 'leverage' ? order : 'asc'}
                    onClick={() => handleSort('leverage')}
                  >
                    <BuildTwoToneIcon color="primary" sx={{ verticalAlign: 'middle' }} />
                  </TableSortLabel>
                </TableCell>

                {/* Value */}
                <TableCell align="right" sx={{ py: 0.5 }}>
                  <MonetizationOnTwoToneIcon color="primary" sx={{ verticalAlign: 'middle' }} />
                </TableCell>

                {/* Liquidation distance */}
                <TableCell align="right" sx={{ py: 0.5 }}>
                  <WaterDropTwoToneIcon color="primary" sx={{ verticalAlign: 'middle' }} />
                </TableCell>

                {/* Travel percent */}
                <TableCell align="right" sx={{ pr: 1, py: 0.5 }}>
                  <PercentTwoToneIcon color="primary" sx={{ verticalAlign: 'middle' }} />
                </TableCell>
              </TableRow>
            </TableHead>

            {/* ================= BODY ================ */}
            <TableBody>
              {sortedPositions.map((pos) => {
                const profitVal = calcProfit(pos) ?? 0;
                const profitHighlight = profitVal > profit_mark;
                const profitColor = profitHighlight ? 'success.main' : 'inherit';
                const profitWeight = profitHighlight ? 700 : 'normal';

                return (
                  <TableRow hover key={pos.id} sx={{ height: POSITION_ROW_HEIGHT }}>
                    {/* Wallet icon */}
                    <TableCell sx={{ pl: 1, py: 0.5 }}>
                      <Avatar
                        src={`/static/images/${(pos.wallet_name || 'unknown')
                          .replace(/\s+/g, '')
                          .replace(/vault$/i, '')
                          .toLowerCase()}_icon.jpg`}
                        alt={pos.wallet_name}
                        sx={{ width: POSITION_ROW_HEIGHT - 4, height: POSITION_ROW_HEIGHT - 4 }}
                      />
                    </TableCell>

                    {/* Asset & position type */}
                    <TableCell sx={{ py: 0.5 }}>
                      <Stack direction="row" alignItems="center" spacing={0.5}>
                        <Avatar
                          src={`/static/images/${(pos.asset_type || 'unknown').toLowerCase()}_logo.png`}
                          alt={pos.asset_type}
                          sx={{ width: POSITION_ROW_HEIGHT - 4, height: POSITION_ROW_HEIGHT - 4 }}
                        />
                        <Typography
                          variant="subtitle2"
                          sx={{ fontSize: POSITION_ROW_HEIGHT * 0.5, lineHeight: 1 }}
                        >
                          {pos.position_type?.toUpperCase()}
                        </Typography>
                      </Stack>
                    </TableCell>

                    {/* Profit (color + bold if above mark) */}
                    <TableCell
                      align="right"
                      sx={{
                        py: 0.5,
                        fontSize: POSITION_ROW_HEIGHT * 0.5,
                        color: profitColor,
                        fontWeight: profitWeight
                      }}
                    >
                      {profitVal.toLocaleString(undefined, {
                        style: 'currency',
                        currency: 'USD',
                        minimumFractionDigits: 2
                      })}
                    </TableCell>

                    {/* Leverage */}
                    <TableCell
                      align="right"
                      sx={{ py: 0.5, fontSize: POSITION_ROW_HEIGHT * 0.5 }}
                    >
                      {Number(pos.leverage || 0).toFixed(2)}
                    </TableCell>

                    {/* Value */}
                    <TableCell
                      align="right"
                      sx={{ py: 0.5, fontSize: POSITION_ROW_HEIGHT * 0.5 }}
                    >
                      ${Number(pos.value || 0).toLocaleString()}
                    </TableCell>

                    {/* Liquidation distance */}
                    <TableCell
                      align="right"
                      sx={{ py: 0.5, fontSize: POSITION_ROW_HEIGHT * 0.5 }}
                    >
                      {pos.liquidation_distance}
                    </TableCell>

                    {/* Travel percent */}
                    <TableCell
                      align="right"
                      sx={{ pr: 1, py: 0.5, fontSize: POSITION_ROW_HEIGHT * 0.5 }}
                    >
                      {`${Number(pos.travel_percent || 0).toFixed(2)}%`}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </PerfectScrollbar>
    </MainCard>
  );
}

PositionListCard.propTypes = { title: PropTypes.string };
