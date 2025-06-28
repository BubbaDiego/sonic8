import PropTypes from 'prop-types';
// material-ui
import Checkbox from '@mui/material/Checkbox';
import IconButton from '@mui/material/IconButton';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TableSortLabel from '@mui/material/TableSortLabel';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// assets
import DeleteIcon from '@mui/icons-material/Delete';

// table header options
const headCells = [
  {
    id: 'id',
    numeric: true,
    label: 'ID'
  },
  {
    id: 'name',
    numeric: false,
    label: 'Name'
  },
  {
    id: 'company',
    numeric: false,
    label: 'Company'
  },
  {
    id: 'phone',
    numeric: false,
    label: 'Phone no'
  },
  {
    id: 'date',
    numeric: false,
    label: 'Follow-up Date'
  },
  {
    id: 'reason',
    numeric: false,
    label: 'Follow-up Reason'
  },
  {
    id: 'priority',
    numeric: false,
    label: 'Priority'
  },
  {
    id: 'status',
    numeric: false,
    label: 'Status',
    align: 'center'
  },
  {
    id: 'notes',
    numeric: false,
    label: 'Notes'
  }
];

// ==============================|| REMINDERS & FOLLOWUP - TABLE TOOLBAR ||============================== //

function EnhancedTableToolbar({ numSelected }) {
  return (
    <Toolbar sx={{ p: 0, px: 1, ...(numSelected > 0 && { color: 'secondary.main' }) }}>
      {numSelected > 0 ? (
        <Typography color="inherit" variant="h4">
          {numSelected} Selected
        </Typography>
      ) : (
        <Typography variant="h6" id="tableTitle">
          Nutrition
        </Typography>
      )}
      <Box sx={{ flexGrow: 1 }} />
      {numSelected > 0 && (
        <Tooltip title="Delete">
          <IconButton size="large">
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      )}
    </Toolbar>
  );
}

// ==============================|| REMINDERS & FOLLOWUP - TABLE HEADER ||============================== //

export default function FollowupTableHeader({ onSelectAllClick, order, orderBy, numSelected, rowCount, onRequestSort, selected }) {
  const createSortHandler = (property) => (event) => {
    onRequestSort(event, property);
  };

  return (
    <TableHead>
      <TableRow>
        <TableCell align="center" padding="checkbox" sx={{ pl: 3 }}>
          <Checkbox
            color="primary"
            indeterminate={numSelected > 0 && numSelected < rowCount}
            checked={rowCount > 0 && numSelected === rowCount}
            onChange={onSelectAllClick}
            slotProps={{ input: { 'aria-label': 'select all desserts' } }}
          />
        </TableCell>
        {numSelected > 0 && (
          <TableCell padding="none" colSpan={10}>
            <EnhancedTableToolbar numSelected={selected.length} />
          </TableCell>
        )}
        {numSelected <= 0 &&
          headCells.map((headCell) => (
            <TableCell
              key={headCell.id}
              align={headCell.align}
              padding={headCell.disablePadding ? 'none' : 'normal'}
              sortDirection={orderBy === headCell.id ? order : false}
            >
              <TableSortLabel
                active={orderBy === headCell.id}
                direction={orderBy === headCell.id ? order : 'asc'}
                onClick={createSortHandler(headCell.id)}
              >
                {headCell.label}
                {orderBy === headCell.id ? (
                  <Typography component="span" sx={{ display: 'none' }}>
                    {order === 'desc' ? 'sorted descending' : 'sorted ascending'}
                  </Typography>
                ) : null}
              </TableSortLabel>
            </TableCell>
          ))}
        {numSelected <= 0 && (
          <TableCell sortDirection={false} align="center" sx={{ pr: 3 }}>
            Action
          </TableCell>
        )}
      </TableRow>
    </TableHead>
  );
}

EnhancedTableToolbar.propTypes = { numSelected: PropTypes.any };

FollowupTableHeader.propTypes = {
  onSelectAllClick: PropTypes.any,
  order: PropTypes.any,
  orderBy: PropTypes.any,
  numSelected: PropTypes.any,
  rowCount: PropTypes.any,
  onRequestSort: PropTypes.any,
  selected: PropTypes.array
};
