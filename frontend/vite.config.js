import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'AgriSaathi — अन्नदाता साथी',
        short_name: 'AgriSaathi',
        description: 'Multilingual AI farming companion for Indian farmers',
        theme_color: '#1a2e1a',
        background_color: '#0d1f0d',
        display: 'standalone',
        scope: '/',
        start_url: '/',
        orientation: 'portrait',
        icons: [
          {
            src: '/icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
      },
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/chat': 'http://localhost:8080',
      '/diagnose': 'http://localhost:8080',
      '/health': 'http://localhost:8080',
      '/token': 'http://localhost:8080',
      '/session': 'http://localhost:8080',
    },
  },
});
