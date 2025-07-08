import PropTypes from 'prop-types';
import { memo } from 'react';
import { useTheme } from '@mui/material/styles';
import Avatar from '@mui/material/Avatar';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import LinearProgress from '@mui/material/LinearProgress';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemAvatar from '@mui/material/ListItemAvatar';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { linearProgressClasses } from '@mui/material/LinearProgress';
import { ThemeMode } from 'config';
import TableChartOutlinedIcon from '@mui/icons-material/TableChartOutlined';
import { useGetLatestPortfolio } from 'api/portfolio';

// Progress Bar Component with dynamic value
function LinearProgressWithLabel({ value, ...others }) {
  const theme = useTheme();

  return (
    <Grid container direction="column" spacing={1} sx={{ mt: 1.5 }}>
      <Grid item>
        <Grid container justifyContent="space-between">
          <Grid item>
            <Typography variant="h6" sx={{ color: theme.palette.mode === ThemeMode.DARK ? 'dark.light' : 'primary.800' }}>
              Progress
            </Typography>
          </Grid>
          <Grid item>
            <Typography variant="h6">{`${Math.round(value)}%`}</Typography>
          </Grid>
        </Grid>
      </Grid>
      <Grid item>
        <LinearProgress
          variant="determinate"
          value={value}
          {...others}
          sx={{
            height: 10,
            borderRadius: 30,
            [`&.${linearProgressClasses.colorPrimary}`]: {
              bgcolor: 'background.paper'
            },
            [`& .${linearProgressClasses.bar}`]: {
              borderRadius: 5,
              bgcolor: 'primary.dark'
            }
          }}
        />
      </Grid>
    </Grid>
  );
}

LinearProgressWithLabel.propTypes = {
  value: PropTypes.number.isRequired
};

// MenuCard updated with portfolio session data
function MenuCard() {
  const theme = useTheme();
  const { portfolio } = useGetLatestPortfolio();

  const currentSessionValue = portfolio?.current_session_value || 0;
  const sessionGoalValue = portfolio?.session_goal_value || 1; // Avoid division by zero
  const progressValue = Math.min((currentSessionValue / sessionGoalValue) * 100, 100);

  return (
    <Card
      sx={{
        bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.main' : 'primary.light',
        mb: 2.75,
        overflow: 'hidden',
        position: 'relative',
        '&:after': {
          content: '""',
          position: 'absolute',
          width: 157,
          height: 157,
          bgcolor: theme.palette.mode === ThemeMode.DARK ? 'dark.dark' : 'primary.200',
          borderRadius: '50%',
          top: -105,
          right: -96
        }
      }}
    >
      <Box sx={{ p: 2 }}>
        <List disablePadding sx={{ pb: 1 }}>
          <ListItem alignItems="flex-start" disableGutters disablePadding>
            <ListItemAvatar sx={{ mt: 0 }}>
              <Avatar
                variant="rounded"
                sx={{
                  ...theme.typography.commonAvatar,
                  ...theme.typography.largeAvatar,
                  color: 'primary.main',
                  border: theme.palette.mode === ThemeMode.DARK ? '1px solid' : 'none',
                  borderColor: 'primary.main',
                  bgcolor: 'background.paper'
                }}
              >
                <TableChartOutlinedIcon fontSize="inherit" />
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              sx={{ mt: 0 }}
              primary={
                <Typography variant="subtitle1" sx={{ color: theme.palette.mode === ThemeMode.DARK ? 'dark.light' : 'primary.800' }}>
                  {currentSessionValue.toLocaleString()}
                </Typography>
              }
              secondary={
                <Typography variant="caption">
                  {`Goal: ${sessionGoalValue.toLocaleString()}`}
                </Typography>
              }
            />
          </ListItem>
        </List>
        <LinearProgressWithLabel value={progressValue} />
      </Box>
    </Card>
  );
}

export default memo(MenuCard);
