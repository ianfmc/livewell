import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    exclude: ['node_modules', '.worktrees/**'],
    coverage: {
      provider: 'v8',
      include: ['src/hooks/**', 'src/components/**', 'src/pages/**'],
      exclude: ['src/components/theme-provider.tsx'],
      thresholds: {
        lines: 80,
      },
    },
  },
})
