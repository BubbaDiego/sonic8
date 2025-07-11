import React from 'react';
import Box from '@mui/material/Box';
import Slider from '@mui/material/Slider';
import useConfig from 'hooks/useConfig';

export default function SidePanelWidthSlider() {
  const { sidePanelWidth, setSidePanelWidth } = useConfig();

  const handleChange = (_, value) => {
    setSidePanelWidth(value);
  };

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 8,
        left: 8,
        right: 8,
        bgcolor: 'background.paper',
        p: 1,
        borderRadius: 1,
        boxShadow: 2,
        zIndex: 1
      }}
    >
      <Slider
        size="small"
        value={sidePanelWidth}
        onChange={handleChange}
        min={200}
        max={600}
        step={10}
        valueLabelDisplay="auto"
      />
    </Box>
  );
}
