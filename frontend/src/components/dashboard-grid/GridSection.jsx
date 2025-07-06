import { useEffect, useState } from 'react';

export default function GridSection({ section, wireframe }) {
  const [widgetRegistry, setWidgetRegistry] = useState(null);

  useEffect(() => {
    import('./registerWidget').then((module) => {
      setWidgetRegistry(module.widgetRegistry);
    });
  }, []);

  if (!widgetRegistry) return null; // or a loader component

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
