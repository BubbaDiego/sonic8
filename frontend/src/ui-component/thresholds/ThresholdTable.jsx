import {
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  TextField,
  Checkbox
} from '@mui/material';

const cols = ['alert_type', 'alert_class', 'condition', 'metric_key', 'low', 'medium', 'high', 'enabled'];

export default function ThresholdTable({ rows, onChange }) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          {cols.map((c) => (
            <TableCell key={c}>{c}</TableCell>
          ))}
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((t) => (
          <TableRow key={t.id}>
            <TableCell>{t.alert_type}</TableCell>
            <TableCell>{t.alert_class}</TableCell>
            <TableCell>{t.condition}</TableCell>
            <TableCell>{t.metric_key}</TableCell>
            <TableCell>
              <TextField
                type="number"
                size="small"
                value={t.low}
                onChange={(e) => onChange(t.id, 'low', Number(e.target.value))}
              />
            </TableCell>
            <TableCell>
              <TextField
                type="number"
                size="small"
                value={t.medium}
                onChange={(e) => onChange(t.id, 'medium', Number(e.target.value))}
              />
            </TableCell>
            <TableCell>
              <TextField
                type="number"
                size="small"
                value={t.high}
                onChange={(e) => onChange(t.id, 'high', Number(e.target.value))}
              />
            </TableCell>
            <TableCell>
              <Checkbox
                checked={!!t.enabled}
                onChange={(e) => onChange(t.id, 'enabled', e.target.checked)}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
