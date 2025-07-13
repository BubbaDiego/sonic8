
import React, { useRef, useState, useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import useSWR, { mutate } from 'swr';
import PortfolioSessionCard from '../../components/PortfolioSessionCard/PortfolioSessionCard';
import DashboardToggle from '../../components/StatusRail/DashboardToggle';
import CompositionPieCard from '../../components/CompositionPieCard/CompositionPieCard';
import PositionListCard from '../../components/PositionListCard/PositionListCard';
import TraderListCard from '../../components/TraderListCard/TraderListCard';
import PerformanceGraphCard from '../../components/PerformanceGraphCard/PerformanceGraphCard';

const fetcher = async (url) => {
  const res = await fetch(url);
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error: ${res.status} ${res.statusText}\n${errorText}`);
  }
  return res.json();
};

const RIGHT_COLUMN_X = 610;
const SIDE_COLUMN_END_X = 800;
const ROW_1_MAX_HEIGHT = 125;
const ROW_2_MAX_HEIGHT = 300;
const ROW_3_MAX_HEIGHT = 500;
const DEBUG_LAYOUT = false;

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

const Dashboard = () => {
  //const { data: snapshot } = useSWR('/api/portfolio/latest_snapshot', fetcher);
  const { data: snapshot } = useSWR('http://localhost:5000/api/portfolio/latest_snapshot', fetcher);


  const handleModify = () => {
    console.log("Modify session clicked");
  };

 const handleReset = async () => {
    await fetch('http://localhost:5000/api/portfolio/reset_session', { method: 'POST' });
    mutate('http://localhost:5000/api/portfolio/latest_snapshot');
  };

  return (
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
      <Section name="Main‑A">
        <DashboardToggle />
      </Section>

      <Section name="Side‑A">
        <CompositionPieCard />
      </Section>

      <Section name="Main‑B">
        <PositionListCard />
      </Section>

      <Section name="Side‑B">
        <TraderListCard title="Trader List" />
      </Section>

      <Section name="Main‑C">
        <PerformanceGraphCard />
      </Section>

      <Section name="Side‑C">
        <PortfolioSessionCard
          snapshot={snapshot}
          onModify={handleModify}
          onReset={handleReset}
        />
      </Section>
    </Box>
  );
};

export default Dashboard;
