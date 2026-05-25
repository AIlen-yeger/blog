import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'
import { musicManifestPlugin } from './scripts/musicManifest'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const base = env.VITE_BASE_PATH || '/'

  return {
  base,
  plugins: [vue(), musicManifestPlugin()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      // 前端 /api/* → 后端 http://localhost:8080/v1/*
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/v1'),
      },
      '/v1/uploads': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
}
})
