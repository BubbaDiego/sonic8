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
export const RIGHT_COLUMN_X = 610;

/**
 * X-coordinate (in px) where the SIDE column ends.
 * Use this to control the width of the right (side) column.
 *
 * Example: 1300 → side column ends at 1300 px
 */
export const SIDE_COLUMN_END_X = 800;

/**
 * Maximum height (in px) allowed for ROW 1.
 */
export const ROW_1_MAX_HEIGHT = 125;

/**
 * Maximum height (in px) allowed for ROW 2.
 */
export const ROW_2_MAX_HEIGHT = 300;

/**
 * Maximum height (in px) allowed for ROW 3.
 */
export const ROW_3_MAX_HEIGHT = 500;

/**
 * Turn visual debug ON/OFF.
 *  true  – every section gets a dashed outline + live coordinates
 *  false – clean production look
 */
export const DEBUG_LAYOUT = false;//true;

/******************************************************************
 *  SECTION + LAYOUT IMPLEMENTATION                               *
 ******************************************************************/

import React, { useRef, useState, useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import StatusRail from '../../components/StatusRail/StatusRail';
import DashboardToggle from '../../components/StatusRail/DashboardToggle';
import CompositionPieCard from '../../components/CompositionPieCard/CompositionPieCard';
import PositionListCard from '../../components/PositionListCard/PositionListCard';
import TraderListCard from '../../components/TraderListCard/TraderListCard';
import PerformanceGraphCard from '../../components/PerformanceGraphCard/PerformanceGraphCard';
import MainCard from 'ui-component/cards/MainCard';

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
        overflowY: 'auto',
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
      gridTemplateColumns: `${RIGHT_COLUMN_X}px ${SIDE_COLUMN_END_X - RIGHT_COLUMN_X}px`,
      gridTemplateRows: `${ROW_1_MAX_HEIGHT}px ${ROW_2_MAX_HEIGHT}px ${ROW_3_MAX_HEIGHT}px`,
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
      <DashboardToggle />
    </Section>

    <Section name="Side‑A">
      <CompositionPieCard />
    </Section>

    {/* ROW 2 */}
    <Section name="Main‑B">
      <PositionListCard />
    </Section>

    <Section name="Side‑B">
      <TraderListCard title="Trader List" />
    </Section>

    {/* ROW 3 */}
    <Section name="Main‑C">
      <PerformanceGraphCard />
    </Section>

    <Section name="Side‑C">
      <StatusRail />
    </Section>
  </Box>
);

export default Dashboard;
