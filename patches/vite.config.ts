import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/positions': 'http://localhost:5000',
      '/sonic_labs': 'http://localhost:5000'
    }
  }
});
