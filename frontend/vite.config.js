import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'SPP — Silknode Production Platform',
        short_name: 'SPP Terminal',
        description: 'Mebel ishlab chiqarish Tsex terminali',
        theme_color: '#6b4226',
        background_color: '#f5efe6',
        display: 'standalone',
        start_url: '/terminal',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        // Heavy WebGL scene loads on-demand only on capable desktops; keep it
        // out of the offline precache so the shop-floor terminal install stays lean.
        globIgnores: ['**/HeroCanvas-*.js'],
        runtimeCaching: [
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/'),
            handler: 'NetworkOnly',
          },
        ],
      },
      // Keep the service worker OUT of dev: an active dev SW intercepts Vite's
      // module requests (/@vite/client, /src/main.jsx, /@react-refresh) and
      // makes them fail to load. The SW is still built for production.
      devOptions: {
        enabled: false,
        type: 'module',
      },
    }),
  ],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
