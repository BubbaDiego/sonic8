import PropTypes from 'prop-types';
import { alpha, useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Chip from '@mui/material/Chip';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { IconBell } from '@tabler/icons-react';
import { ThemeMode } from 'config';

const sevColor = { HIGH: 'error', MEDIUM: 'warning', LOW: 'success' };

function ListItemWrapper({ children }) {
  const theme = useTheme();
  return (
    <Box
      sx={{
        p: 2,
        borderBottom: '1px solid',
        borderColor: 'divider',
        cursor: 'pointer',
        '&:hover': {
          bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.900' : alpha(theme.palette.grey[200], 0.3)
        }
      }}
    >
      {children}
    </Box>
  );
}

export default function NotificationList({ items }) {
  const theme = useTheme();
  const containerSX = { pl: 7 };

  if (!items?.length) {
    return (
      <Typography variant='body2' sx={{ p: 2 }}>
        No notifications
      </Typography>
    );
  }

  return (
    <List sx={{ width: '100%', maxWidth: { xs: 300, md: 330 }, py: 0 }}>
      {items.map((n) => {
        const created = new Date(n.created_at);
        const ageMin = Math.floor((Date.now() - created.getTime()) / 60000);
        const sev = sevColor[n.level] || 'primary';

        return (
          <ListItemWrapper key={n.id}>
            <ListItem
              alignItems='center'
              disablePadding
              secondaryAction={
                <Stack direction='row' sx={{ alignItems: 'center', justifyContent: 'flex-end' }}>
                  <Typography variant='caption'>{ageMin} min ago</Typography>
                </Stack>
              }
            >
              <ListItemAvatar>
                <Avatar
                  sx={{
                    color: `${sev}.dark`,
                    bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : `${sev}.light`
                  }}
                >
                  <IconBell stroke={1.5} size='20px' />
                </Avatar>
              </ListItemAvatar>
              <ListItemText primary={<Typography variant='subtitle1'>{n.subject}</Typography>} />
            </ListItem>
            <Stack spacing={2} sx={containerSX}>
              <Typography variant='subtitle2'>{n.body.split('\n')[0]}</Typography>
              <Stack direction='row' spacing={1} sx={{ alignItems: 'center' }}>
                {!n.read && <Chip label='Unread' color='error' size='small' sx={{ width: 'min-content' }} />}
                {ageMin < 5 && <Chip label='New' color='warning' size='small' sx={{ width: 'min-content' }} />}
              </Stack>
            </Stack>
          </ListItemWrapper>
        );
      })}
    </List>
  );
}

NotificationList.propTypes = { items: PropTypes.array };