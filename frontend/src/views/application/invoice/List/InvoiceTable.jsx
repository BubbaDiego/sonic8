import PropTypes from 'prop-types';
import * as React from 'react';
import { Link } from 'react-router-dom';

// material-ui
import Chip from '@mui/material/Chip';
import Avatar from '@mui/material/Avatar';
import Checkbox from '@mui/material/Checkbox';
import IconButton from '@mui/material/IconButton';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';

// third party
import { random } from 'lodash-es';

// project imports
import InvoiceTableHeader from './InvoiceTableHeader';
import MainCard from 'ui-component/cards/MainCard';
import { ImagePath, getImageUrl } from 'utils/getImageUrl';

// assets
import VisibilityTwoToneIcon from '@mui/icons-material/VisibilityTwoTone';
import EditTwoToneIcon from '@mui/icons-material/EditTwoTone';
import DeleteTwoToneIcon from '@mui/icons-material/DeleteTwoTone';

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

// ==============================|| INVOICE LIST - TABLE ||============================== //

export default function InvoiceTable({ rows }) {
  const [order, setOrder] = React.useState('asc');
  const [orderBy, setOrderBy] = React.useState('calories');
  const [selected, setSelected] = React.useState([]);
  const [page, setPage] = React.useState(0);
  const [rowsPerPage, setRowsPerPage] = React.useState(5);

  let label;
  let color;

  const handleRequestSort = (event, property) => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  const handleSelectAllClick = (event) => {
    if (event.target.checked) {
      if (selected.length > 0) {
        setSelected([]);
      } else {
        const newSelectedId = rows.map((n) => n.customer_name);
        setSelected(newSelectedId);
      }
      return;
    }
    setSelected([]);
  };

  const handleCheckBox = (event, name) => {
    const selectedIndex = selected.indexOf(name);
    let newSelected = [];

    if (selectedIndex === -1) {
      newSelected = newSelected.concat(selected, name);
    } else if (selectedIndex === 0) {
      newSelected = newSelected.concat(selected.slice(1));
    } else if (selectedIndex === selected.length - 1) {
      newSelected = newSelected.concat(selected.slice(0, -1));
    } else if (selectedIndex > 0) {
      newSelected = newSelected.concat(selected.slice(0, selectedIndex), selected.slice(selectedIndex + 1));
    }

    setSelected(newSelected);
  };

  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event) => {
    event?.target.value && setRowsPerPage(parseInt(event?.target.value, 10));
    setPage(0);
  };

  const isSelected = (name) => selected.indexOf(name) !== -1;
  const emptyRows = page > 0 ? Math.max(0, (1 + page) * rowsPerPage - rows.length) : 0;

  return (
    <MainCard content={false}>
      {/* table */}
      <TableContainer>
        <Table sx={{ minWidth: 750 }} aria-labelledby="tableTitle">
          <InvoiceTableHeader
            numSelected={selected.length}
            order={order}
            orderBy={orderBy}
            onSelectAllClick={handleSelectAllClick}
            onRequestSort={handleRequestSort}
            rowCount={rows.length}
            selected={selected}
          />
          <TableBody>
            {stableSort(rows, getComparator(order, orderBy))
              .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
              .map((row, index) => {
                /** Make sure no display bugs if row isn't an OrderData object */
                if (typeof row === 'number') return null;

                const isItemSelected = isSelected(row.customer_name);
                const labelId = `enhanced-table-checkbox-${index}`;

                switch (row.status.toString()) {
                  case 'Paid':
                    label = 'Paid';
                    color = 'success';
                    break;
                  case 'Cancelled':
                    label = 'Cancelled';
                    color = 'error';
                    break;
                  case 'Unpaid':
                  default:
                    label = 'Unpaid';
                    color = 'warning';
                    break;
                }

                return (
                  <TableRow hover role="checkbox" aria-checked={isItemSelected} tabIndex={-1} key={index} selected={isItemSelected}>
                    <TableCell padding="checkbox" sx={{ pl: 3 }} onClick={(event) => handleCheckBox(event, row.customer_name)}>
                      <Checkbox color="primary" checked={isItemSelected} slotProps={{ input: { 'aria-labelledby': labelId } }} />
                    </TableCell>
                    <TableCell>{row.date}</TableCell>
                    <TableCell>
                      <Typography variant="h5" align="center">
                        #{row.invoice_id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={2}>
                        <Avatar alt="" src={getImageUrl(`avatar-${row.avatar}.png`, ImagePath.USERS)} />
                        <Stack>
                          <Typography variant="subtitle1">{row.customer_name}</Typography>
                          <Typography variant="caption">{row.email}</Typography>
                        </Stack>
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip label={label} size="small" color={color} />
                    </TableCell>
                    <TableCell>{row.due_date}</TableCell>
                    <TableCell align="right">${row.quantity}</TableCell>
                    <TableCell align="right">${random(1000, 9999)}</TableCell>
                    <TableCell align="right">${random(1000, 9999)}</TableCell>
                    <TableCell align="center" sx={{ pr: 3 }}>
                      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'center' }}>
                        <Tooltip title="View">
                          <IconButton color="primary" component={Link} to={'/apps/invoice/invoice-details'} size="small" aria-label="View">
                            <VisibilityTwoToneIcon sx={{ fontSize: '1.3rem' }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Edit">
                          <IconButton color="secondary" component={Link} to={`/apps/invoice/edit-invoice`} size="small" aria-label="Edit">
                            <EditTwoToneIcon sx={{ fontSize: '1.3rem' }} />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Delete">
                          <IconButton color="error" size="small" aria-label="Delete">
                            <DeleteTwoToneIcon sx={{ fontSize: '1.3rem' }} />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </TableCell>
                  </TableRow>
                );
              })}
            {emptyRows > 0 && (
              <TableRow sx={{ height: 53 * emptyRows }}>
                <TableCell colSpan={10} />
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      {/* table pagination */}
      <TablePagination
        rowsPerPageOptions={[5, 10, 25]}
        component="div"
        count={rows.length}
        rowsPerPage={rowsPerPage}
        page={page}
        onPageChange={handleChangePage}
        onRowsPerPageChange={handleChangeRowsPerPage}
      />
    </MainCard>
  );
}

InvoiceTable.propTypes = { rows: PropTypes.array };
