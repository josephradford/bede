import { resolve } from "path";
import { defineConfig } from "vite";
import { htmlInjectionPlugin } from "vite-plugin-html-inject";

export default defineConfig({
  root: "src",
  plugins: [htmlInjectionPlugin()],
  build: {
    outDir: "../dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "src/index.html"),
        tasks: resolve(__dirname, "src/tasks.html"),
        memories: resolve(__dirname, "src/memories.html"),
        goals: resolve(__dirname, "src/goals.html"),
        conversations: resolve(__dirname, "src/conversations.html"),
      },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
