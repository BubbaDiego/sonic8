import { Link } from 'react-router-dom';

// material-ui
import Button from '@mui/material/Button';
import CardMedia from '@mui/material/CardMedia';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

// project imports
import { DASHBOARD_PATH } from 'config';
import AnimateButton from 'ui-component/extended/AnimateButton';
import { gridSpacing } from 'store/constant';

// assets
import HomeTwoToneIcon from '@mui/icons-material/HomeTwoTone';
import emptyImage from 'assets/images/maintenance/empty.svg';

// ==============================|| FORBIDDEN PAGE ||============================ //

export default function Forbidden() {
  return (
    <Stack sx={{ gap: gridSpacing, alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <Box sx={{ width: { xs: 350, sm: 396 } }}>
        <CardMedia component="img" src={emptyImage} alt="forbidden" style={{ height: '100%', width: '100%' }} />
      </Box>
      <Stack spacing={gridSpacing} sx={{ justifyContent: 'center', alignItems: 'center', p: 1.5 }}>
        <Typography variant="h1">Access Forbidden</Typography>
        <Typography variant="body2" align="center">
          You do not have permission to access this page.
        </Typography>
        <AnimateButton>
          <Button variant="contained" size="large" component={Link} to={DASHBOARD_PATH}>
            <HomeTwoToneIcon sx={{ fontSize: '1.3rem', mr: 0.75 }} /> Home
          </Button>
        </AnimateButton>
      </Stack>
    </Stack>
  );
}
