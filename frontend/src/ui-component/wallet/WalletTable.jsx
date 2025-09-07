import {
  Avatar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  IconButton,
  Button,
  Stack,
  Tooltip,
  Typography
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import RefreshIcon from '@mui/icons-material/Refresh';
import CircularProgress from '@mui/material/CircularProgress';
import { VerifiedSolCell, TopTokensChips, VerifiedStatusCell } from 'components/wallets/VerifiedCells';

function AddressCell({ row }) {
  const a = row._addr || row.public_address || '';
  const short = a ? `${a.slice(0, 6)}…${a.slice(-6)}` : '';
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Typography variant="body2">{short}</Typography>
      <Tooltip title="Copy address">
        <IconButton size="small" onClick={() => navigator.clipboard.writeText(a)}>
          <ContentCopyIcon fontSize="inherit" />
        </IconButton>
      </Tooltip>
      <Button size="small" variant="text" href={`https://solscan.io/account/${a}`} target="_blank" rel="noreferrer">
        Solscan
      </Button>
    </Stack>
  );
}

function PositionsCell({ row }) {
  return (
    <Stack alignItems="flex-end" spacing={0}>
      <Typography variant="subtitle2">${Number(row.balance || 0).toLocaleString()}</Typography>
      <Typography variant="caption" color="text.secondary">source: positions</Typography>
    </Stack>
  );
}

function VerifiedCell({ row }) {
  return <VerifiedSolCell value={row.verifiedSol} rentLamports={row.rentLamports} loading={row.isVerifying} />;
}

function TopCell({ row }) {
  return <TopTokensChips top={row.top} limit={4} />;
}

function StatusCell({ row }) {
  return (
    <VerifiedStatusCell
      verifiedAt={row.verifiedAt}
      error={row.verifyError}
      detail={row.verifyErrorDetail ?? row.detail}
    />
  );
}

function ActionsCell({ row, onEdit, onDelete, onVerifyOne }) {
  const a = row._addr || row.public_address;
  return (
    <Stack direction="row" spacing={0.5}>
      <Tooltip title="Verify now">
        <span>
          <IconButton size="small" onClick={() => onVerifyOne(a, { force: true })} disabled={!a || row.isVerifying}>
            {row.isVerifying ? <CircularProgress size={16} /> : <RefreshIcon fontSize="inherit" />}
          </IconButton>
        </span>
      </Tooltip>
      <IconButton size="small" onClick={() => onEdit(row)}>
        <EditIcon fontSize="inherit" />
      </IconButton>
      <IconButton size="small" onClick={() => onDelete(row.name)}>
        <DeleteIcon fontSize="inherit" />
      </IconButton>
    </Stack>
  );
}

const WalletTable = ({ rows, onEdit, onDelete, onVerifyAll, onVerifyOne }) => (
  <Stack spacing={1}>
    <Stack direction="row" spacing={1} justifyContent="flex-start">
      <Button variant="contained" size="small" onClick={onVerifyAll}>
        Verify All
      </Button>
      <Button variant="outlined" size="small" onClick={() => onVerifyAll(true)}>
        Force Verify All
      </Button>
    </Stack>
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>🖼️</TableCell>
          <TableCell>🧠 Name</TableCell>
          <TableCell>📬 Address</TableCell>
          <TableCell align="right">Positions ($)</TableCell>
          <TableCell align="right">Verified SOL</TableCell>
          <TableCell sx={{ minWidth: 160 }}>Top tokens</TableCell>
          <TableCell>Status</TableCell>
          <TableCell>🛠️ Actions</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((w) => (
          <TableRow key={w.name}>
            <TableCell>
              <Avatar alt={w.name} src={w.image_path || '/images/unknown_wallet.jpg'} sx={{ width: 32, height: 32 }} />
            </TableCell>
            <TableCell>{w.name}</TableCell>
            <TableCell><AddressCell row={w} /></TableCell>
            <TableCell align="right"><PositionsCell row={w} /></TableCell>
            <TableCell align="right"><VerifiedCell row={w} /></TableCell>
            <TableCell sx={{ minWidth: 160 }}><TopCell row={w} /></TableCell>
            <TableCell><StatusCell row={w} /></TableCell>
            <TableCell><ActionsCell row={w} onEdit={onEdit} onDelete={onDelete} onVerifyOne={onVerifyOne} /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </Stack>
);

export default WalletTable;
