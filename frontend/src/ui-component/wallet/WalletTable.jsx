import React from 'react';
import { Avatar, Table, TableBody, TableCell, TableHead, TableRow, IconButton } from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';

const WalletTable = ({ rows, onEdit, onDelete }) => (
  <Table size="small">
    <TableHead>
      <TableRow>
        <TableCell>🖼️</TableCell>
        <TableCell>🧠 Name</TableCell>
        <TableCell>📬 Address</TableCell>
        <TableCell align="right">💰 Balance</TableCell>
        <TableCell>🛠️ Actions</TableCell>
      </TableRow>
    </TableHead>
    <TableBody>
      {rows.map((w) => (
        <TableRow key={w.name}>
          <TableCell>
            <Avatar
              alt={w.name}
              src={w.image_path || '/images/unknown_wallet.jpg'}
              sx={{ width: 32, height: 32 }}
            />
          </TableCell>
          <TableCell>{w.name}</TableCell>
          <TableCell title={w.public_address}>
            {w.public_address.slice(0, 4)}…{/* ellipsis */}
          </TableCell>
          <TableCell align="right">${w.balance.toFixed(2)}</TableCell>
          <TableCell>
            <IconButton size="small" onClick={() => onEdit(w)}>
              <EditIcon fontSize="inherit" />
            </IconButton>
            <IconButton size="small" onClick={() => onDelete(w.name)}>
              <DeleteIcon fontSize="inherit" />
            </IconButton>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
);

export default WalletTable;
