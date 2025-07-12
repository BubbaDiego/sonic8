import React from 'react';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import { useTheme } from '@mui/material/styles';
import useMediaQuery from '@mui/material/useMediaQuery';

import useConfig from 'hooks/useConfig';
import PositionTableCard from './PositionTableCard';
import CompositionPieCard from '../dashboard/CompositionPieCard';
import SidePanelWidthSlider from './SidePanelWidthSlider';

const PositionsPage = () => {
  const theme = useTheme();
  const isPhone = useMediaQuery(theme.breakpoints.down('sm'));
  const { sidePanelWidth } = useConfig();

  return (
    <Box
      sx={{ display: 'flex', flexDirection: isPhone ? 'column' : 'row', width: '100%', gap: 2 }}
    >
      <Box sx={{ flex: 1 }}>
        <PositionTableCard />
      </Box>
      {isPhone ? (
        <Drawer anchor="bottom" open variant="temporary">
          <Box sx={{ p: 2 }}>
            <CompositionPieCard />
          </Box>
        </Drawer>
      ) : (
        <Box sx={{ width: sidePanelWidth, position: 'relative' }}>
          <SidePanelWidthSlider />
          <CompositionPieCard />
        </Box>
      )}
    </Box>
  );
};

export default PositionsPage;
