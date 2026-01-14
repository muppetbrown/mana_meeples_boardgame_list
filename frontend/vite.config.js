import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import viteCompression from 'vite-plugin-compression';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Gzip compression
    viteCompression({
      algorithm: 'gzip',
      ext: '.gz',
      threshold: 1024, // Only compress files larger than 1KB
      deleteOriginFile: false,
    }),
    // Brotli compression (better compression than gzip)
    viteCompression({
      algorithm: 'brotliCompress',
      ext: '.br',
      threshold: 1024,
      deleteOriginFile: false,
    }),
  ],

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
    sourcemap: process.env.NODE_ENV === 'development', // Only generate source maps in dev mode
    // Optimize chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'dompurify': ['dompurify'], // Separate chunk for lazy-loaded dependency
        },
        // Optimize chunk naming for better caching
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      }
    },
    // Enable minification
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
      },
    },
    // Optimize chunk size warnings
    chunkSizeWarningLimit: 600,
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
    // Coverage configuration
    coverage: {
      provider: 'v8', // Use V8 coverage provider (faster than istanbul)
      reporter: ['text', 'json', 'html', 'lcov'],
      reportsDirectory: './coverage',
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.test.{js,jsx,ts,tsx}',
        '**/__tests__/**',
        '**/__mocks__/**',
        'src/reportWebVitals.js',
        'src/setupTests.js',
        'vite.config.js',
        'postcss.config.cjs',
        'tailwind.config.cjs',
        'build/',
        'dist/',
        'coverage/',
      ],
      include: [
        'src/**/*.{js,jsx,ts,tsx}'
      ],
      all: true, // Include all files, not just tested ones
      // Coverage thresholds - Set to current baseline to prevent regression
      // Can be gradually increased as test coverage improves
      statements: 40,
      branches: 40,
      functions: 45,
      lines: 40,
      // Fail build if coverage is below thresholds
      thresholds: {
        statements: 40,
        branches: 40,
        functions: 45,
        lines: 40,
      },
    },
  }
});
