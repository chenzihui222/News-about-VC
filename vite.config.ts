import vinext from "vinext";
import { cloudflare } from "@cloudflare/vite-plugin";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vinext(), cloudflare()],
  build: {
    rollupOptions: {
      external: ["blake3-wasm"],
    },
  },
});
