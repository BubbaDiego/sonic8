import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// routing
import router from 'routes';

// project imports
import Locales from 'ui-component/Locales';
import NavigationScroll from 'layout/NavigationScroll';
import Snackbar from 'ui-component/extended/Snackbar';
import Notistack from 'ui-component/third-party/Notistack';
import ThemeCustomization from 'themes';

// auth provider
import { JWTProvider as AuthProvider } from 'contexts/JWTContext';

// Initialize React Query Client
const queryClient = new QueryClient();

// ==============================|| APP ||============================== //

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeCustomization>
        <Locales>
          <NavigationScroll>
            <AuthProvider>
              <Notistack>
                <RouterProvider router={router} />
                <Snackbar />
              </Notistack>
            </AuthProvider>
          </NavigationScroll>
        </Locales>
      </ThemeCustomization>
    </QueryClientProvider>
  );
}
