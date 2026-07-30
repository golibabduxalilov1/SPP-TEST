import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  build: { rollupOptions: { input: 'ds-preview.html' }, outDir: 'ds-preview-dist', emptyOutDir: true },
})
