import { Table, TableHead, TableRow, TableCell, TableBody, TextField } from '@mui/material';

export default function CooldownTable({ values, onChange }) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>name</TableCell>
          <TableCell>value</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {Object.entries(values).map(([k, v]) => (
          <TableRow key={k}>
            <TableCell>{k}</TableCell>
            <TableCell>
              <TextField
                type="number"
                size="small"
                value={v}
                onChange={(e) => onChange(k, Number(e.target.value))}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
