import { defineConfig } from 'vite';
export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Keep the console's script files as separate entry points so the existing
    // <script src="app.js"> tags keep working after build.
    rollupOptions: {
      input: {
        app: 'app.js',
        charts: 'charts.js',
        simulation: 'simulation.js',
        actions: 'actions.js',
        runbook: 'runbook.js',
        styles: 'src/style.css',
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.type === 'asset' && /\.css$/.test(assetInfo.name || '')) {
            return 'assets/[name][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        },
      },
    },
  },
});
