import PropTypes from 'prop-types';


// ==============================|| AUTH GUARD ||============================== //

/**
 * Authentication guard for routes
 * @param {PropTypes.node} children children element/node
 */
export default function AuthGuard({ children }) {
  return children;
}

AuthGuard.propTypes = { children: PropTypes.any };
