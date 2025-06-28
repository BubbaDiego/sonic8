import PropTypes from 'prop-types';
import { createContext, useEffect, useState } from 'react';

// third party
import { Auth0Provider as AuthProvider, useAuth0 } from '@auth0/auth0-react';

// project imports
import Loader from 'ui-component/Loader';

// constant
const initialState = {
  isLoggedIn: false,
  isInitialized: false,
  user: null
};

const domain = import.meta.env.VITE_APP_AUTH0_DOMAIN;
const clientId = import.meta.env.VITE_APP_AUTH0_CLIENT_ID;

// ==============================|| AUTH0 CONTEXT & PROVIDER ||============================== //

const Auth0Context = createContext(null);

export function Auth0Provider({ children }) {
  return (
    <AuthProvider
      domain={domain}
      clientId={clientId}
      authorizationParams={{
        redirect_uri: window.location.origin
      }}
    >
      <Auth0ContextProvider>{children}</Auth0ContextProvider>
    </AuthProvider>
  );
}

function Auth0ContextProvider({ children }) {
  const { isAuthenticated, user, isLoading, loginWithPopup, logout } = useAuth0();

  // State to track the authentication status and user information
  const [state, setState] = useState(initialState);

  useEffect(() => {
    if (!isLoading) {
      // Update state when authentication status is available
      setState({
        isLoggedIn: isAuthenticated,
        isInitialized: true,
        user: isAuthenticated
          ? {
              id: user?.sub,
              avatar: user?.picture,
              email: user?.email,
              name: user?.name,
              tier: 'Premium' // Set tier or other user-specific data if needed
            }
          : null
      });
    }
  }, [isAuthenticated, isLoading, user]);

  const loginAuth = async (options) => {
    await loginWithPopup(options);
  };

  const logoutAuth = () => {
    logout();
  };

  const resetPassword = async (email) => {
    // Implement reset password functionality if needed
  };

  const updateProfile = () => {
    // Implement update profile functionality if needed
  };

  if (isLoading || !state.isInitialized) {
    return <Loader />;
  }

  const contextValue = {
    ...state, // Spread the current state (isLoggedIn, isInitialized, user)
    loginAuth,
    logout: logoutAuth,
    resetPassword,
    updateProfile
  };

  return <Auth0Context value={contextValue}>{children}</Auth0Context>;
}

export default Auth0Context;

Auth0Provider.propTypes = { children: PropTypes.node };

Auth0ContextProvider.propTypes = { children: PropTypes.node };
