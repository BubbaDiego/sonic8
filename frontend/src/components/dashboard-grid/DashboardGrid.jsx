import PropTypes from 'prop-types';
import Grid from 'components/AppGrid';
import GridSection from './GridSection';

/**
 * Top‑level renderer: feed it a layout JSON and it paints the dashboard.
 */
export default function DashboardGrid({ layout, wireframe = false }) {
  return (
    <Grid container spacing={layout.spacing ?? 3}>
      {layout.sections.map((section) => (
        <GridSection
          key={section.id}
          section={section}
          wireframe={wireframe}
        />
      ))}
    </Grid>
  );
}

DashboardGrid.propTypes = {
  layout : PropTypes.object.isRequired,   // validated at runtime
  wireframe : PropTypes.bool
};
