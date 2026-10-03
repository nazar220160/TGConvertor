import { defineConfig } from 'vite';

export default defineConfig(({ command }) => ({
  base: './',
  // Vite injects style tags during HMR; production keeps the stricter static CSP.
  plugins:
    command === 'serve'
      ? [
          {
            name: 'dev-styles',
            transformIndexHtml: (html: string) =>
              html.replace("style-src 'self';", "style-src 'self' 'unsafe-inline';"),
          },
        ]
      : [],
  build: { target: 'es2022', sourcemap: false },
  worker: { format: 'es' },
}));
