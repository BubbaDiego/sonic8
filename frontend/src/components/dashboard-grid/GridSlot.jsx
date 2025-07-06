import PropTypes from 'prop-types';
import Grid from 'components/AppGrid';      // the size‑prop shim
import Typography from '@mui/material/Typography';
import { useTheme } from '@mui/material/styles';

/**
 * A single placeholder cell.
 * When `wireframe` === true it shows a tinted box + ID label.
 * Otherwise it renders the registered widget for this slot ID.
 */
export default function GridSlot({ slotDef, wireframe, Widget }) {
  const theme = useTheme();
  const {
    size,
    bg = wireframe ? 'secondary.light' : 'transparent',
    label = slotDef.id.toUpperCase()
  } = slotDef;

  return (
    <Grid size={size} sx={{
      bgcolor: bg,
      border: wireframe ? `1px dashed ${theme.palette.divider}` : 'none',
      minHeight: 120,
      position: 'relative',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      {wireframe
        ? <Typography variant="subtitle1">{label}</Typography>
        : Widget && <Widget />}
    </Grid>
  );
}

GridSlot.propTypes = {
  slotDef : PropTypes.object.isRequired,
  wireframe : PropTypes.bool,
  Widget : PropTypes.elementType        // may be undefined in wireframe mode
};
