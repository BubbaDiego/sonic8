import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';
import Avatar from '@mui/material/Avatar';
import CardActions from '@mui/material/CardActions';
import Chip from '@mui/material/Chip';
import ClickAwayListener from '@mui/material/ClickAwayListener';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Popper from '@mui/material/Popper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import MainCard from 'ui-component/cards/MainCard';
import Transitions from 'ui-component/extended/Transitions';
import NotificationList from './NotificationList';
import { ThemeMode } from 'config';
import { IconBell } from '@tabler/icons-react';

const statusOptions = [
  { value: 'all', label: 'All Notification' },
  { value: 'new', label: 'New' },
  { value: 'unread', label: 'Unread' }
];

export default function NotificationSection() {
  const theme = useTheme();
  const downMD = useMediaQuery(theme.breakpoints.down('md'));
  const anchorRef = useRef(null);
  const prevOpen = useRef(false);

  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('all');
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);

  // Fetch helper
  const fetchData = async () => {
    const list = await fetch(`/api/notifications?status=${filter}`).then(r => r.json());
    setItems(list);
    const { count } = await fetch('/api/notifications/unread-count').then(r => r.json());
    setUnread(count);
  };

  // Poll when dropdown opens or filter changes
  useEffect(() => {
    if (open) fetchData();
    /* eslint-disable react-hooks/exhaustive-deps */
  }, [open, filter]);

  // close focus handling
  useEffect(() => {
    if (prevOpen.current === true && open === false && anchorRef.current) {
      anchorRef.current.focus();
    }
    prevOpen.current = open;
  }, [open]);

  const handleToggle = () => setOpen((prev) => !prev);
  const handleClose = (event) => {
    if (anchorRef.current && anchorRef.current.contains(event.target)) return;
    setOpen(false);
  };

  const markAllRead = async () => {
    await fetch('/api/notifications/mark_all_read', { method: 'POST' });
    setUnread(0);
    setItems((arr) => arr.map((it) => ({ ...it, read: 1 })));
  };

  return (
    <>
      <Box sx={{ ml: 2 }}>
        <Avatar
          variant='rounded'
          sx={{
            ...theme.typography.commonAvatar,
            ...theme.typography.mediumAvatar,
            transition: 'all .2s ease-in-out',
            bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'secondary.light',
            color: theme.palette.mode === ThemeMode.DARK ? 'warning.dark' : 'secondary.dark',
            '&:hover': {
              bgcolor: theme.palette.mode === ThemeMode.DARK ? 'warning.dark' : 'secondary.dark',
              color: theme.palette.mode === ThemeMode.DARK ? 'grey.800' : 'secondary.light'
            }
          }}
          ref={anchorRef}
          aria-controls={open ? 'menu-list-grow' : undefined}
          aria-haspopup='true'
          onClick={handleToggle}
        >
          <IconBell stroke={1.5} size='20px' />
        </Avatar>
      </Box>
      <Popper
        placement={downMD ? 'bottom' : 'bottom-end'}
        open={open}
        anchorEl={anchorRef.current}
        role={undefined}
        transition
        disablePortal
        modifiers={[{ name: 'offset', options: { offset: [downMD ? 5 : 0, 20] } }]}
      >
        {({ TransitionProps }) => (
          <ClickAwayListener onClickAway={handleClose}>
            <Transitions position={downMD ? 'top' : 'top-right'} in={open} {...TransitionProps}>
              <Paper>
                {open && (
                  <MainCard border={false} elevation={16} content={false} boxShadow>
                    <Grid container direction='column' spacing={2}>
                      <Grid item xs={12}>
                        <Grid container sx={{ alignItems: 'center', justifyContent: 'space-between', pt: 2, px: 2 }}>
                          <Grid item>
                            <Stack direction='row' spacing={2}>
                              <Typography variant='subtitle1'>All Notification</Typography>
                              <Chip
                                size='small'
                                label={String(unread).padStart(2, '0')}
                                sx={{ color: 'background.default', bgcolor: 'warning.dark' }}
                              />
                            </Stack>
                          </Grid>
                          <Grid item>
                            <Typography
                              component={Link}
                              to='#'
                              variant='subtitle2'
                              color='primary'
                              onClick={markAllRead}
                            >
                              Mark as all read
                            </Typography>
                          </Grid>
                        </Grid>
                      </Grid>

                      <Grid item xs={12}>
                        <Box
                          sx={{
                            height: '100%',
                            maxHeight: 'calc(100vh - 205px)',
                            overflowX: 'hidden',
                            '&::-webkit-scrollbar': { width: 5 }
                          }}
                        >
                          <Grid container direction='column' spacing={2}>
                            <Grid item xs={12}>
                              <Box sx={{ px: 2, pt: 0.25 }}>
                                <TextField
                                  select
                                  fullWidth
                                  value={filter}
                                  onChange={(e) => setFilter(e.target.value)}
                                  SelectProps={{ native: true }}
                                >
                                  {statusOptions.map((opt) => (
                                    <option key={opt.value} value={opt.value}>
                                      {opt.label}
                                    </option>
                                  ))}
                                </TextField>
                              </Box>
                            </Grid>
                            <Grid item xs={12}>
                              <Divider sx={{ my: 0 }} />
                            </Grid>
                          </Grid>

                          <NotificationList items={items} />
                        </Box>
                      </Grid>
                    </Grid>
                    <CardActions sx={{ p: 1.25, justifyContent: 'center' }}>
                      <Button size='small' disableElevation component={Link} to='/notifications'>
                        View All
                      </Button>
                    </CardActions>
                  </MainCard>
                )}
              </Paper>
            </Transitions>
          </ClickAwayListener>
        )}
      </Popper>
    </>
  );
}