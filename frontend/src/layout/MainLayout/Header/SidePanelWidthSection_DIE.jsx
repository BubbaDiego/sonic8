import { useState } from 'react';
import IconButton from '@mui/material/IconButton';
import Popover from '@mui/material/Popover';
import Slider from '@mui/material/Slider';
import Box from '@mui/material/Box';
import TuneIcon from '@mui/icons-material/Tune';
import useConfig from 'hooks/useConfig';

export default function SidePanelWidthSection() {
  const { sidePanelWidth, setSidePanelWidth } = useConfig();
  const [anchorEl, setAnchorEl] = useState(null);

  const handleOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const open = Boolean(anchorEl);
  const id = open ? 'sidepanel-width-popover' : undefined;

  const handleChange = (_, value) => {
    setSidePanelWidth(value);
  };

  return (
    <Box sx={{ ml: 1 }}>
      <IconButton aria-describedby={id} onClick={handleOpen} size="large">
        <TuneIcon />
      </IconButton>
      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Box sx={{ p: 2, width: 200 }}>
          <Slider value={sidePanelWidth} onChange={handleChange} min={200} max={600} step={10} valueLabelDisplay="auto" />
        </Box>
      </Popover>
    </Box>
  );
}
