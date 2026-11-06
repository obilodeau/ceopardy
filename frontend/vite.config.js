import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// Vite config for the Ceopardy front-end.
//
// In dev, proxy /api and /socket.io to the Flask back-end (default 127.0.0.1:5000)
// so that the SPA can be served on localhost:5173 while hitting Flask APIs.
//
// In production, `npm run build` emits to ../ceopardy/static/dist which Flask
// serves out of the package's static folder (and ships in the wheel).
//
// buzzer.html and soundboard.html are more entries: the players' and the
// sound operator's pages, served from the guest port. The manifest tells that
// server exactly which files those pages load, and it serves nothing else.
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://127.0.0.1:5000',
        ws: true,
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/guest-io': {
        target: 'http://127.0.0.1:5001',
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../ceopardy/static/dist',
    emptyOutDir: true,
    assetsDir: 'assets',
    sourcemap: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: fileURLToPath(new URL('./index.html', import.meta.url)),
        buzzer: fileURLToPath(new URL('./buzzer.html', import.meta.url)),
        soundboard: fileURLToPath(new URL('./soundboard.html', import.meta.url)),
      },
    },
  },
})
