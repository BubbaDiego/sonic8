import { isRouteErrorResponse, useRouteError } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

export default function ErrorBoundary() {
  const error = useRouteError();

  if (isRouteErrorResponse(error)) {
    return (
      <Alert color="error">
        Error {error.status} - {error.statusText}
      </Alert>
    );
  }

  return (
    <Box sx={{ p: 4, bgcolor: 'background.paper' }}>
      <Typography variant="h4" gutterBottom>
        An unexpected error occurred.
      </Typography>
      <Typography variant="body1" color="text.secondary">
        {error?.message || "No error details available."}
      </Typography>
    </Box>
  );
}
