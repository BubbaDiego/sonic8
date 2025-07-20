import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

// ==============================|| Vite Config (patched) ||============================== //
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  // Sub‑folder where the built site will live, or '/' for root.
  const BASE_NAME = env.VITE_APP_BASE_NAME || '/';
  // FastAPI host that the dev server should proxy to.
  const API_URL = env.VITE_APP_API_URL || 'http://localhost:5000';
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
        }
      }
    },
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
    plugins: [react(), tsconfigPaths()]
  };
});
