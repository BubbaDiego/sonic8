import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      // project aliases
      'routes': path.resolve(__dirname, 'src/routes'),
      'config': path.resolve(__dirname, 'src/config'),
      'hooks': path.resolve(__dirname, 'src/hooks'),
      'ui-component': path.resolve(__dirname, 'src/ui-component'),
      'components': path.resolve(__dirname, 'src/components'),
      'store': path.resolve(__dirname, 'src/store'),
      'contexts': path.resolve(__dirname, 'src/contexts'),
      'utils': path.resolve(__dirname, 'src/utils'),
      'assets': path.resolve(__dirname, 'src/assets'),
      'views': path.resolve(__dirname, 'src/views'),
      'api': path.resolve(__dirname, 'src/api'),
      'menu-items': path.resolve(__dirname, 'src/menu-items')
    }
  },
  server: {
    host: true,
    port: 3000,
    strictPort: true
  }
});
