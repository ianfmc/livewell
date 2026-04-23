import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    exclude: ['node_modules', '.worktrees/**'],
    coverage: {
      provider: 'v8',
      include: ['src/hooks/**', 'src/components/**', 'src/pages/**'],
      exclude: ['src/components/theme-provider.tsx'],
      thresholds: { lines: 80 },
    },
  },
})
