import PropTypes from 'prop-types';
import * as React from 'react';

// material-ui
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';

// third party
import { Chance } from 'chance';
import { random } from 'lodash-es';

// project imports
import RefundTableHeader from './RefundHeader';

// table sort
function descendingComparator(a, b, orderBy) {
  if (b[orderBy] < a[orderBy]) {
    return -1;
  }
  if (b[orderBy] > a[orderBy]) {
    return 1;
  }
  return 0;
}

const getComparator = (order, orderBy) =>
  order === 'desc' ? (a, b) => descendingComparator(a, b, orderBy) : (a, b) => -descendingComparator(a, b, orderBy);

function stableSort(array, comparator) {
  const stabilizedThis = array.map((el, index) => [el, index]);
  stabilizedThis.sort((a, b) => {
    const order = comparator(a[0], b[0]);
    if (order !== 0) return order;
    return a[1] - b[1];
  });
  return stabilizedThis.map((el) => el[0]);
}

// ==============================|| REFUND - TABLE ||============================== //

export default function RefundTable({ rows }) {
  const chance = new Chance();

  const [order, setOrder] = React.useState('asc');
  const [orderBy, setOrderBy] = React.useState('calories');
  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(10);

  const handleRequestSort = (event, property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    event?.target.value && setRowsPerPage(parseInt(event?.target.value, 10));
    setPage(0);
  };

  const emptyRows = page > 0 ? Math.max(0, (1 + page) * rowsPerPage - rows.length) : 0;

  return (
    <>
      <TableContainer>
        <Table sx={{ minWidth: 750 }} aria-labelledby="tableTitle">
          <RefundTableHeader order={order} orderBy={orderBy} onRequestSort={handleRequestSort} />
          <TableBody>
            {stableSort(rows, getComparator(order, orderBy))
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((row, index) => {
                /** Make sure no display bugs if row isn't an OrderData object */
                if (typeof row === 'number') return null;
                const Amount = Math.floor(Math.random() * 150) + 1;
                const date = new Date(new Date().getTime() - random(0, 28) * 24 * 60 * 60 * 1000);

                return (
                  <TableRow hover role="checkbox" tabIndex={-1} key={index}>
                    <TableCell sx={{ pl: 3 }}>{date.getDate() + '.' + (date.getMonth() + 1) + '.' + date.getFullYear()}</TableCell>
                    <TableCell>
                      <Typography variant="h5">{row.name.slice(0, -2)}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography>{chance.phone()}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="h5">{chance.company()}</Typography>
                      <Typography variant="subtitle2" noWrap>
                        #{row.id}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">${row.qty} </TableCell>
                    <TableCell align="right" sx={{ pr: 3 }}>
                      <Typography {...(Amount < 30 && { color: 'error.main' })}>${Amount}</Typography>
                    </TableCell>
                  </TableRow>
                );
              })}
            {emptyRows > 0 && (
              <TableRow sx={{ height: 53 * emptyRows }}>
                <TableCell colSpan={6} />
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* table pagination */}
      <TablePagination
        rowsPerPageOptions={[10, 25]}
        component="div"
        count={rows.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
    </>
  );
}

RefundTable.propTypes = { rows: PropTypes.array };
