import PropTypes from 'prop-types';
import { useState } from 'react';

// material-ui
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Box from '@mui/material/Box';

// project imports
import MainCard from 'ui-component/cards/MainCard';

function a11yProps(index) {
  return {
    id: `simple-tab-${index}`,
    'aria-controls': `simple-tabpanel-${index}`
  };
}

// ==============================|| BLOG DETAILS - HEADING TAB ||============================== //

export default function HeadingTab({ tabs }) {
  const [tabValue, setTabValue] = useState(0);
  const handleChange = (event, newValue) => {
    setTabValue(newValue);
  };

  return (
    <MainCard content={false}>
      <Box sx={{ mx: 3 }}>
        <Tabs
          value={tabValue}
          variant="scrollable"
          onChange={handleChange}
          sx={{
            '&.MuiTabs-root .MuiTab-root': {
              minHeight: 'auto',
              minWidth: 10,
              py: 1.75,
              px: 1,
              mr: 2.2,
              color: 'grey.600',
              '&.Mui-selected': { color: 'primary.main' }
            },
            '& .MuiTabs-flexContainer': { border: 0 },
            '& .MuiTabs-indicator': { height: 3 }
          }}
        >
          {tabs.map((tab, index) => (
            <Tab key={index} label={tab.label} icon={tab.icon} iconPosition="start" {...a11yProps(index)} />
          ))}
        </Tabs>
      </Box>
    </MainCard>
  );
}

HeadingTab.propTypes = { tabs: PropTypes.array };
