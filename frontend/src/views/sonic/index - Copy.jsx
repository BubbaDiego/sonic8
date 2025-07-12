/******************************************************************
 *  GLOBAL LAYOUT CONFIG (tweak‑me zone)                          *
 ******************************************************************/

/**
 * X-coordinate (in px) where the RIGHT column begins.
 * Practically, this is also the width of the big LEFT column.
 *
 * Example: 920 → left column = 920 px wide, right column sticks
 * to its right edge.
 */
export const RIGHT_COLUMN_X = 920;

/**
 * Turn visual debug ON/OFF.
 *  true  – every section gets a dashed outline + live coordinates
 *  false – clean production look
 */
export const DEBUG_LAYOUT = true;

/******************************************************************
 *  SECTION + LAYOUT IMPLEMENTATION                               *
 ******************************************************************/

import React, { useRef, useState, useEffect } from 'react';
import MainCard from 'ui-component/cards/MainCard';
import { Box, Typography } from '@mui/material';
import DashboardToggle from '../../components/StatusRail/DashboardToggle';

const Section = ({ name, children, debug = DEBUG_LAYOUT }) => {
  const ref = useRef(null);
  const [rect, setRect] = useState(null);

  useEffect(() => {
    if (debug && ref.current) setRect(ref.current.getBoundingClientRect());
  }, [debug]);

  return (
    <Box
      ref={ref}
      sx={{
        position: 'relative',
        p: 1,
        outline: debug ? '2px dashed crimson' : 'none',
      }}
    >
      {debug && rect && (
        <Typography
          variant="caption"
          sx={{
            position: 'absolute',
            top: 2,
            left: 4,
            background: 'rgba(255,255,255,0.7)',
            px: 0.5,
            py: 0,
            fontSize: 10,
            zIndex: 10,
          }}
        >
          {name} — x:{Math.round(rect.x)} y:{Math.round(rect.y)} w:
          {Math.round(rect.width)} h:{Math.round(rect.height)}
        </Typography>
      )}
      {children}
    </Box>
  );
};

const Dashboard = () => (
  <Box
    sx={{
      display: 'grid',
      gridTemplateColumns: `${RIGHT_COLUMN_X}px 1fr`,
      gridAutoRows: 'minmax(180px, auto)',
      columnGap: 2,
      rowGap: 2,
      height: '100%',
      width: '100%',
      position: 'relative',
      p: 2,
      boxSizing: 'border-box',
    }}
  >
    {/* ROW 1 */}
    <Section name="Main‑A">
      <MainCard title="Main A">
        <DashboardToggle />
        <Typography sx={{ mt: 2 }}>
          Left – big area.
        </Typography>
      </MainCard>
    </Section>

    <Section name="Side‑A">
      <MainCard title="Side A">
        <Typography>Right column card.</Typography>
      </MainCard>
    </Section>

    {/* ROW 2 */}
    <Section name="Main‑B">
      <MainCard title="Main B">
        <Typography>Another big card.</Typography>
      </MainCard>
    </Section>

    <Section name="Side‑B">
      <MainCard title="Side B">
        <Typography>Skinny column again.</Typography>
      </MainCard>
    </Section>
  </Box>
);

export default Dashboard;
