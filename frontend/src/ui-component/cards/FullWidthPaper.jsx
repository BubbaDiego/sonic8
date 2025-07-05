import { Paper, TableContainer } from '@mui/material';

const FullWidthPaper = ({ children }) => (
  <TableContainer component={Paper} sx={{ width: '100%', minWidth: 0, overflowX: 'auto' }}>
    {children}
  </TableContainer>
);

export default FullWidthPaper;
