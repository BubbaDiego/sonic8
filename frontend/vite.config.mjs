import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import jsconfigPaths from 'vite-jsconfig-paths';

// ==============================|| Vite Config (patched) ||============================== //
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  // Sub‑folder where the built site will live, or '/' for root.
  const BASE_NAME = env.VITE_APP_BASE_NAME || '/';
  // FastAPI host that the dev server should proxy to.
  const API_URL = env.VITE_APP_API_URL || 'http://127.0.0.1:8000';
  const PORT = 3000;

  return {
    server: {
      open: true,
      port: PORT,
      host: true,
      hmr: {
        overlay: true
      },
      proxy: {
        // Forward every request that starts with /cyclone to the backend
        '/cyclone': {
          target: API_URL,
          changeOrigin: true,
          secure: false
        },

        '/positions': {
          target: API_URL,
          changeOrigin: true,
          secure: false
        },

        '/sonic_labs': {
          target: API_URL,
          changeOrigin: true,
          secure: false
        },

        '/api': {
          target: API_URL,
          changeOrigin: true,
          secure: false
        }
      }
    },
    // Serve static assets from "frontend/static" at the site root.
    // Example: file at frontend/static/images/wally.png -> reachable at /images/wally.png
    publicDir: 'static',
    build: {
      chunkSizeWarningLimit: 1600
    },
    preview: {
      open: true,
      host: true
    },
    define: {
      global: 'window'
    },
    resolve: {
      alias: {
        '@tabler/icons-react': '@tabler/icons-react/dist/esm/icons/index.mjs'
      },
      extensions: ['.js', '.jsx', '.ts', '.tsx']
    },
    base: BASE_NAME,
    plugins: [react(), jsconfigPaths()]
  };
});
