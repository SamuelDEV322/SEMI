import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "..", "VITE_");
  const proxy = {
    "/api": {
      target: env.VITE_BACKEND_TARGET || "http://127.0.0.1:8000",
      changeOrigin: false,
    },
  };
  return {
    plugins: [react(), tailwindcss()],
    envDir: "..",
    server: { port: 5173, strictPort: true, proxy },
    preview: { port: 4173, proxy },
  };
});
