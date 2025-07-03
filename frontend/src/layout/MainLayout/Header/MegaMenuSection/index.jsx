import PropTypes from 'prop-types';
import { useRef, useState } from 'react';

// material-ui
import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import ClickAwayListener from '@mui/material/ClickAwayListener';
import Grid from '@mui/material/Grid';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListSubheader from '@mui/material/ListSubheader';
import ListItemText from '@mui/material/ListItemText';
import Paper from '@mui/material/Paper';
import Popper from '@mui/material/Popper';
import Typography from '@mui/material/Typography';

// project imports
import { ThemeDirection, ThemeMode } from 'config';
import MainCard from 'ui-component/cards/MainCard';
import Transitions from 'ui-component/extended/Transitions';
import { drawerWidth, gridSpacing } from 'store/constant';
import useConfig from 'hooks/useConfig';

// assets
import Banner from './Banner';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import { IconAccessPoint } from '@tabler/icons-react';

function HeaderAvatar({ children, sx, ref, ...others }) {
  const theme = useTheme();

  return (
    <Avatar
      ref={ref}
      sx={{
        ...theme.typography.commonAvatar,
        ...theme.typography.mediumAvatar,
        display: { xs: 'none', md: 'flex' },
        bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'secondary.light',
        color: theme.palette.mode === ThemeMode.DARK ? 'secondary.main' : 'secondary.dark',
        '&:hover': {
          bgcolor: theme.palette.mode === ThemeMode.DARK ? 'secondary.main' : 'secondary.dark',
          color: theme.palette.mode === ThemeMode.DARK ? 'secondary.light' : 'secondary.light'
        }
      }}
      {...others}
    >
      {children}
    </Avatar>
  );
}

const linkList = [
  {
    id: 'user-quick',
    label: 'User Quick',
    children: [
      { label: 'Social Profile' },
      { label: 'Account Profile' },
      { label: 'User Cards' },
      { label: 'User List' },
      { label: 'Contact' }
    ]
  },
  {
    id: 'application',
    label: 'Applications',
    children: [{ label: 'Chat' }, { label: 'Kanban' }, { label: 'Mail' }, { label: 'Calendar' }, { label: 'E-commerce' }]
  },
  {
    id: 'primitives',
    label: 'Primitives',
    children: [{ label: 'Colors' }, { label: 'Typography' }, { label: 'Shadows' }, { label: 'Icons' }, { label: 'Elements' }]
  }
];

// ==============================|| SEARCH INPUT - MEGA MENu||============================== //

export default function MegaMenuSection() {
  const theme = useTheme();
  const { themeDirection } = useConfig();

  const [open, setOpen] = useState(false);
  const anchorRef = useRef(null);

  const handleToggle = () => {
    setOpen((prevOpen) => !prevOpen);
  };

  const handleClose = (event) => {
    if (anchorRef.current && anchorRef.current.contains(event.target)) {
      return;
    }
    setOpen(false);
  };

  return (
    <>
      <HeaderAvatar
        variant="rounded"
        ref={anchorRef}
        aria-controls={open ? 'menu-list-grow' : undefined}
        aria-haspopup="true"
        onClick={handleToggle}
      >
        <IconAccessPoint stroke={1.5} size="20px" />
      </HeaderAvatar>
      <Popper
        placement="bottom-end"
        open={open}
        anchorEl={anchorRef.current}
        role={undefined}
        transition
        sx={{ ...(themeDirection === ThemeDirection.RTL && { right: { md: '-170px !important', lg: '-300px !important' } }) }}
        disablePortal
        modifiers={[
          {
            name: 'offset',
            options: {
              offset: [150, 20]
            }
          }
        ]}
      >
        {({ TransitionProps }) => (
          <ClickAwayListener onClickAway={handleClose}>
            <Transitions in={open} {...TransitionProps}>
              <Paper
                sx={{
                  width: {
                    md: `calc(100vw - 100px)`,
                    lg: `calc(100vw - ${drawerWidth + 100}px)`,
                    xl: `calc(100vw - ${drawerWidth + 140}px)`
                  },
                  maxWidth: { xl: 900, md: 764 }
                }}
              >
                {open && (
                  <MainCard
                    border={false}
                    elevation={16}
                    content={false}
                    boxShadow
                    shadow={theme.shadows[16]}
                    sx={{ overflow: { p: 1, xs: 'visible', md: 'hidden' } }}
                  >
                    <Grid container spacing={gridSpacing}>
                      <Grid size={{ md: 4 }}>
                        <Banner />
                      </Grid>
                      <Grid size={{ md: 8 }}>
                        <Grid
                          container
                          spacing={gridSpacing}
                          sx={{
                            pt: 3,
                            '& .MuiListItemButton-root:hover': {
                              bgcolor: 'transparent',
                              '& .MuiTypography-root': {
                                color: 'secondary.main'
                              }
                            },
                            '& .MuiListItemIcon-root': {
                              minWidth: 16
                            }
                          }}
                        >
                          {linkList.map((links, index) => (
                            <Grid key={index} size={4}>
                              <List
                                component="nav"
                                aria-labelledby={`list-${links.id}`}
                                subheader={
                                  <ListSubheader id={`list-${links.id}`}>
                                    <Typography variant="subtitle1">{links.label}</Typography>
                                  </ListSubheader>
                                }
                              >
                                {links.children.map((items, index) => (
                                  <ListItemButton key={index}>
                                    <ListItemIcon>
                                      <FiberManualRecordIcon sx={{ fontSize: '0.5rem' }} />
                                    </ListItemIcon>
                                    <ListItemText primary={items.label} />
                                  </ListItemButton>
                                ))}
                              </List>
                            </Grid>
                          ))}
                        </Grid>
                      </Grid>
                    </Grid>
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

HeaderAvatar.propTypes = { children: PropTypes.node, sx: PropTypes.any, ref: PropTypes.any, others: PropTypes.any };
