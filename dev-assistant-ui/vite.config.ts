import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { viteSingleFile } from 'vite-plugin-singlefile'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    viteSingleFile(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      'fontawesome.css': '@fortawesome/fontawesome-free/css/all.min.css',
      'highlight.css': 'highlight.js/styles/github-dark.min.css',
    },
  },
  build: {
    sourcemap: true,
    rollupOptions: {
      input: {
        app: './chat.html',
      },
    },
  },
})
