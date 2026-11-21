import { defineConfig } from 'vite';
import type { Plugin } from 'vite';
import react from '@vitejs/plugin-react';

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * 把 JS 和 CSS 全部内联进 index.html，并把入口包打成 IIFE。
 * 这样构建产物是一个可以双击打开的单文件——file:// 协议下
 * 模块脚本会被 CORS 拦截，只有内联的经典脚本能跑。
 */
function inlineSingleFile(): Plugin {
  return {
    name: 'inline-single-file',
    enforce: 'post',
    generateBundle(_options, bundle) {
      const htmlKey = Object.keys(bundle).find((k) => k.endsWith('.html'));
      if (!htmlKey) return;
      const htmlAsset = bundle[htmlKey] as { source: string };
      let html = String(htmlAsset.source);

      for (const [key, raw] of Object.entries(bundle)) {
        const file = raw as {
          type: string;
          fileName: string;
          code?: string;
          source?: string | Uint8Array;
        };
        const base = file.fileName.split('/').pop() ?? file.fileName;

        if (file.type === 'chunk' && file.code) {
          html = html.replace(
            new RegExp(`<script[^>]*src="[^"]*${escapeRegExp(base)}"[^>]*></script>`),
            '',
          );
          html = html.replace(
            '</body>',
            `<script>\n${file.code}\n</script>\n</body>`,
          );
          delete bundle[key];
        } else if (file.type === 'asset' && base.endsWith('.css')) {
          html = html.replace(
            new RegExp(`<link[^>]*href="[^"]*${escapeRegExp(base)}"[^>]*>`),
            '',
          );
          html = html.replace('</head>', `<style>\n${String(file.source)}\n</style>\n</head>`);
          delete bundle[key];
        }
      }

      htmlAsset.source = html;
    },
  };
}

export default defineConfig({
  plugins: [react(), inlineSingleFile()],
  base: './',
  build: {
    target: 'es2020',
    cssCodeSplit: false,
    assetsInlineLimit: 100_000_000,
    rollupOptions: {
      output: {
        format: 'iife',
        inlineDynamicImports: true,
      },
    },
  },
  server: {
    port: 5173,
    host: '127.0.0.1',
    watch: {
      // 编辑器/工具写入时产生的临时文件会让 chokidar 报 EBUSY 直接崩掉进程
      ignored: [
        '**/.shots/**',
        '**/.npm-cache/**',
        '**/.npm-logs/**',
        '**/.tmp/**',
        '**/*.tmp',
        '**/.*.tmpdir/**',
      ],
    },
  },
});
