import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import ClickAwayListener from '@mui/material/ClickAwayListener';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Paper from '@mui/material/Paper';
import Popper from '@mui/material/Popper';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { FormattedMessage } from 'react-intl';
import { ThemeMode } from 'config';
import MainCard from 'ui-component/cards/MainCard';
import Transitions from 'ui-component/extended/Transitions';
import useAuth from 'hooks/useAuth';
import useConfig from 'hooks/useConfig';
import { IconLogout, IconSettings, IconUser, IconDatabase, IconAntennaBars5 } from '@tabler/icons-react';

// Updated to new icon
const SonicBurstIcon = '/static/images/bubba_icon.png';


// SettingsSection component
export default function SettingsSection() {
  const theme = useTheme();
  const { mode, borderRadius } = useConfig();
  const navigate = useNavigate();
  const [sdm, setSdm] = useState(true);
  const [notification, setNotification] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const { logout, user } = useAuth();
  const [open, setOpen] = useState(false);
  const anchorRef = useRef(null);

  // ---------- 👋 Dynamic greeting logic (2 am–10 am / 10 am–6 pm / 6 pm–2 am) ----------
  const getGreeting = () => {
    const hr = new Date().getHours();
    if (hr >= 2 && hr < 10) return 'Good Morning';
    if (hr >= 10 && hr < 18) return 'Good Day';
    return 'Good Evening';
  };
  const greeting = getGreeting();
  const displayName = 'Bubba'; // Always greet the boss as Bubba
  // ---------- end greeting logic ----------

  const handleLogout = async () => {
    try {
      await logout();
    } catch (err) {
      console.error(err);
    }
  };

  const handleListItemClick = (event, index, route = '') => {
    setSelectedIndex(index);
    handleClose(event);
    if (route && route !== '') {
      navigate(route);
    }
  };

  const handleToggle = () => {
    setOpen((prevOpen) => !prevOpen);
  };

  const handleClose = (event) => {
    if (anchorRef.current && anchorRef.current.contains(event.target)) {
      return;
    }
    setOpen(false);
  };

  useEffect(() => {
    anchorRef.current?.focus();
  }, [open]);

  return (
    <>
      <Chip
        sx={{
          ml: 2,
          height: '48px',
          alignItems: 'center',
          borderRadius: '27px',
          '& .MuiChip-label': { lineHeight: 0 }
        }}
        icon={
          <Avatar
            src={SonicBurstIcon} // replaced icon clearly
            alt="bubba-icon"
            sx={{
              ...theme.typography.mediumAvatar,
              margin: '8px 0 8px 8px !important',
              cursor: 'pointer'
            }}
            ref={anchorRef}
            aria-haspopup="true"
          />
        }
        label={<IconSettings stroke={1.5} size="24px" />}
        onClick={handleToggle}
        color="primary"
        aria-label="system-options"
      />
      <Popper
        placement="bottom"
        open={open}
        anchorEl={anchorRef.current}
        transition
        disablePortal
        modifiers={[{ name: 'offset', options: { offset: [0, 14] } }]}
      >
        {({ TransitionProps }) => (
          <ClickAwayListener onClickAway={handleClose}>
            <Transitions in={open} {...TransitionProps}>
              <Paper>
                {open && (
                  <MainCard elevation={16} boxShadow shadow={theme.shadows[16]}>
                    <Box sx={{ p: 2, pb: 0 }}>
                      <Stack>
                        {/* ---------- Original static greeting preserved (now commented) ---------- */}
                        {/*
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <Typography variant="h4">Good Morning,</Typography>
                          <Typography variant="h4" sx={{ fontWeight: 400 }}>
                            {user?.name}
                          </Typography>
                        </Stack>
                        */}
                        {/* ---------- New dynamic greeting ---------- */}
                        <Stack direction="row" spacing={0.5} alignItems="center">
                          <Typography variant="h4">{greeting},</Typography>
                          <Typography variant="h4" sx={{ fontWeight: 400 }}>
                            {displayName}
                          </Typography>
                        </Stack>
                        {/* ---------- end dynamic greeting ---------- */}
                      </Stack>
                      <Divider />
                    </Box>
                    <Box sx={{ p: 2, py: 0, height: '100%', overflowX: 'hidden' }}>
                      <Card sx={{ bgcolor: mode === ThemeMode.DARK ? 'dark.800' : 'primary.light', my: 2 }}>
                        <CardContent>
                          <Grid container spacing={3} direction="column">
                            <Grid container justifyContent="space-between" alignItems="center">
                              <Typography variant="subtitle1">Start DND Mode</Typography>
                              <Switch
                                color="primary"
                                checked={sdm}
                                onChange={(e) => setSdm(e.target.checked)}
                                size="small"
                              />
                            </Grid>
                            <Grid container justifyContent="space-between" alignItems="center">
                              <Typography variant="subtitle1">Allow Notifications</Typography>
                              <Switch
                                checked={notification}
                                onChange={(e) => setNotification(e.target.checked)}
                                size="small"
                              />
                            </Grid>
                          </Grid>
                        </CardContent>
                      </Card>
                      <Divider />
                      <List sx={{ width: '100%', maxWidth: 350, borderRadius: `${borderRadius}px` }}>
                        <ListItemButton selected={selectedIndex === 0} onClick={(event) => handleListItemClick(event, 0)}>
                          <ListItemIcon>
                            <IconSettings stroke={1.5} size="20px" />
                          </ListItemIcon>
                          <ListItemText primary={<Typography variant="body2"><FormattedMessage id="account-settings" /></Typography>} />
                        </ListItemButton>
                        <ListItemButton selected={selectedIndex === 1} onClick={(event) => handleListItemClick(event, 1)}>
                          <ListItemIcon>
                            <IconUser stroke={1.5} size="20px" />
                          </ListItemIcon>
                          <ListItemText primary={<Typography variant="body2"><FormattedMessage id="social-profile" /></Typography>} />
                        </ListItemButton>
                        <ListItemButton
                          selected={selectedIndex === 3}
                          onClick={(e) => handleListItemClick(e, 2, '/communications/xcom')}
                        >
                          <ListItemIcon>
                            <IconAntennaBars5 stroke={1.5} size="20px" />
                          </ListItemIcon>
                          <ListItemText primary={<Typography variant="body2">XCom Settings</Typography>} />
                        </ListItemButton>
                        <ListItemButton
                          selected={selectedIndex === 3}
                          onClick={(e) => handleListItemClick(e, 3, '/debug/db')}
                        >
                          <ListItemIcon>
                            <IconDatabase stroke={1.5} size="20px" />
                          </ListItemIcon>
                          <ListItemText primary={<Typography variant="body2"><FormattedMessage id="database-viewer" defaultMessage="Database Viewer" /></Typography>} />
                        </ListItemButton>
                        <ListItemButton onClick={handleLogout}>
                          <ListItemIcon>
                            <IconLogout stroke={1.5} size="20px" />
                          </ListItemIcon>
                          <ListItemText primary={<Typography variant="body2"><FormattedMessage id="logout" /></Typography>} />
                        </ListItemButton>
                      </List>
                    </Box>
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
