import PropTypes from 'prop-types';


// ==============================|| GUEST GUARD ||============================== //

/**
 * Guest guard for routes having no auth required
 * @param {PropTypes.node} children children element/node
 */

export default function GuestGuard({ children }) {
  return children;
}

GuestGuard.propTypes = { children: PropTypes.any };
