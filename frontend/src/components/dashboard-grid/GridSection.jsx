// src/components/dashboard-grid/GridSection.jsx
import PropTypes from 'prop-types';
import Grid from 'components/AppGrid';      // ⬅ keeps the size‑prop shim
import GridSlot from './GridSlot';
import { widgetRegistry } from './registerWidget';   // static import — simplest

export default function GridSection({ section, wireframe }) {
  const { size, slots, bg = wireframe ? 'primary.light' : 'transparent' } = section;

  return (
    <Grid size={size} sx={{ bgcolor: bg }}>
      <Grid container spacing={section.spacing ?? 0}>
        {slots.map((slot) => (
          <GridSlot
            key={slot.id}
            slotDef={slot}
            wireframe={wireframe}
            Widget={widgetRegistry[slot.id]}
          />
        ))}
      </Grid>
    </Grid>
  );
}

GridSection.propTypes = {
  section : PropTypes.object.isRequired,
  wireframe : PropTypes.bool
};
