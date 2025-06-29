import PropTypes from 'prop-types';
import { createContext } from 'react';

// ==============================|| NO-AUTH CONTEXT & PROVIDER ||============================== //

const JWTContext = createContext({
  isLoggedIn: true,
  isInitialized: true,
  user: null,
  login: async () => {},
  logout: () => {},
  register: async () => {},
  resetPassword: async () => {},
  updateProfile: () => {}
});

export function JWTProvider({ children }) {
  const context = {
    isLoggedIn: true,
    isInitialized: true,
    user: null,
    login: async () => {},
    logout: () => {},
    register: async () => {},
    resetPassword: async () => {},
    updateProfile: () => {}
  };

  return <JWTContext.Provider value={context}>{children}</JWTContext.Provider>;
}

export default JWTContext;

JWTProvider.propTypes = { children: PropTypes.node };
