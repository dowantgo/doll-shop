import { createServer } from 'vite'
import vue from '@vitejs/plugin-vue'

async function start() {
  const server = await createServer({
    configFile: false,
    cacheDir: '.vite',
    plugins: [vue()],
    optimizeDeps: {
      disabled: true
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      strictPort: true,
      open: true,
      allowedHosts: ['bethany-noncompulsive-kristine.ngrok-free.dev'],
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '/api')
        }
      }
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      minify: 'terser'
    }
  })

  await server.listen()
  server.printUrls()
}

start().catch((err) => {
  console.error('Failed to start Vite dev server:', err)
  process.exit(1)
})
