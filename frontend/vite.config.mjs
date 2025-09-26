import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Helper to resolve to /src/*
const r = (p = '') => path.resolve(__dirname, 'src', p);

// IMPORTANT: keep these in sync with jsconfig.json "paths"
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  const BASE_NAME = env.VITE_APP_BASE_NAME || '/';
  const API_URL = env.VITE_APP_API_URL || 'http://127.0.0.1:8000';
  const PORT = Number(env.VITE_PORT || 3000);

  return {
    base: BASE_NAME,
    plugins: [react()],
    server: {
      port: PORT,
      strictPort: true,
      host: true,
      open: true,
      hmr: { overlay: true },
      proxy: {
        '/api': { target: API_URL, changeOrigin: true, secure: false },
        '/cyclone': { target: API_URL, changeOrigin: true, secure: false },
        '/sonic_labs': { target: API_URL, changeOrigin: true, secure: false }
      }
    },
    preview: {
      open: true,
      host: true
    },
    build: {
      chunkSizeWarningLimit: 1600
    },
    resolve: {
      alias: {
        '@': r(),
        routes: r('routes'),
        layout: r('layout'),
        themes: r('themes'),
        theme: r('theme'),
        'ui-component': r('ui-component'),
        components: r('components'),
        views: r('views'),
        store: r('store'),
        utils: r('utils'),
        assets: r('assets'),
        images: r('assets/images'),
        'menu-items': r('menu-items'),
        contexts: r('contexts'),
        hooks: r('hooks'),
        config: r('config'),
        api: r('api'),
        '@tabler/icons-react': '@tabler/icons-react/dist/esm/icons/index.mjs'
      }
    },
    define: {
      global: 'window'
    }
  };
});
