import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The panel is served behind a reverse proxy in the Docker stack; the backend
// module answers under /api. In dev we proxy /api to the FastAPI service.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
