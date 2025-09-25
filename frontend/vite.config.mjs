// vite.config.mjs
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import jsconfigPaths from 'vite-jsconfig-paths';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  // Optional envs if you use them
  const BASE_NAME = env.VITE_APP_BASE_NAME || '/';
  const API_URL   = env.VITE_APP_API_URL   || 'http://127.0.0.1:8000';
  const PORT      = Number(env.VITE_PORT || 3000);

  return {
    base: BASE_NAME,

    server: {
      open: true,
      host: true,
      port: PORT,
      hmr: { overlay: true },
      proxy: {
        // keep or delete if you don't need these
        '/api':        { target: API_URL, changeOrigin: true, secure: false },
        '/cyclone':    { target: API_URL, changeOrigin: true, secure: false },
        '/sonic_labs': { target: API_URL, changeOrigin: true, secure: false }
      }
    },

    preview: { open: true, host: true },

    build: { chunkSizeWarningLimit: 1600 },

    resolve: {
      alias: {
        // QoL
        '@': path.resolve(__dirname, 'src'),

        // Aliases used in your imports (map each to src/<folder>)
        'routes':       path.resolve(__dirname, 'src/routes'),
        'config':       path.resolve(__dirname, 'src/config'),
        'themes':       path.resolve(__dirname, 'src/themes'),
        'contexts':     path.resolve(__dirname, 'src/contexts'),
        'utils':        path.resolve(__dirname, 'src/utils'),
        'api':          path.resolve(__dirname, 'src/api'),
        'views':        path.resolve(__dirname, 'src/views'),
        'store':        path.resolve(__dirname, 'src/store'),
        'hooks':        path.resolve(__dirname, 'src/hooks'),
        'layout':       path.resolve(__dirname, 'src/layout'),
        'ui-component': path.resolve(__dirname, 'src/ui-component'),

        // keep your icon ESM alias if you use Tabler
        '@tabler/icons-react': '@tabler/icons-react/dist/esm/icons/index.mjs'
      },
      extensions: ['.mjs', '.js', '.jsx', '.ts', '.tsx', '.json']
    },

    plugins: [
      react(),
      // also honors jsconfig/tsconfig "paths" if present
      jsconfigPaths()
    ],

    define: {
      global: 'window'
    }
  };
});
