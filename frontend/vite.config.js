import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // Development server configuration
  server: {
    port: 3000,
    open: true,
    // Proxy API requests during development
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  },

  // Build configuration
  build: {
    outDir: 'build',
    sourcemap: true,
    // Optimize chunk splitting
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
        }
      }
    }
  },

  // PWA configuration
  // Service worker and manifest.json are in /public and will be copied as-is to build output
  // This ensures the service worker is at the root level for proper scope

  // Enable CSS modules
  css: {
    modules: {
      localsConvention: 'camelCase'
    }
  },

  // Preview server (for testing production builds)
  preview: {
    port: 3000,
    open: true
  },

  // Define global constants
  define: {
    'process.env': {}
  },

  // Vitest configuration
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    css: true,
  }
});
