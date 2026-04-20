import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig, loadEnv} from 'vite';

export default defineConfig(({mode}) => {
  const env = loadEnv(mode, '.', '');
  return {
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'blindference-wasm-mime',
        configureServer(server) {
          server.middlewares.use((req, res, next) => {
            if (req.url?.includes('.wasm')) {
              res.setHeader('Content-Type', 'application/wasm');
            }
            next();
          });
        },
        configurePreviewServer(server) {
          server.middlewares.use((req, res, next) => {
            if (req.url?.includes('.wasm')) {
              res.setHeader('Content-Type', 'application/wasm');
            }
            next();
          });
        },
      },
    ],
    worker: {
      format: 'es',
    },
    optimizeDeps: {
      exclude: ['@cofhe/sdk', '@cofhe/sdk/web', '@cofhe/sdk/chains', 'tfhe', 'tweetnacl'],
    },
    define: {
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
        tfhe: path.resolve(__dirname, 'src/lib/tfhe-wrapper.ts'),
        tweetnacl: path.resolve(__dirname, 'src/lib/tweetnacl-wrapper.ts'),
        'tweetnacl/nacl-fast.js': path.resolve(__dirname, 'src/lib/tweetnacl-wrapper.ts'),
      },
    },
    server: {
      host: '127.0.0.1',
      port: 3000,
      hmr: process.env.DISABLE_HMR !== 'true',
    },
    preview: {
      host: '127.0.0.1',
      port: 3000,
    },
  };
});
