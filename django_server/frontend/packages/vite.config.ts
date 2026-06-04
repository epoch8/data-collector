import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/static/packages/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: process.env.DJANGO_STATIC_OUT
      ? path.resolve(__dirname, process.env.DJANGO_STATIC_OUT)
      : path.resolve(__dirname, '../../api/static/packages'),
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: path.resolve(__dirname, 'index.html'),
    },
  },
  server: {
    proxy: {
      '/ui/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/ui/login': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
