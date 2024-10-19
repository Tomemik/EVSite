import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

// https://vitejs.dev/config/
export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  let proxyUrl: string = "http://localhost:8000",
    host: boolean = false;
  try {
    if (env.VITE_PROXY_URL) proxyUrl = env.VITE_PROXY_URL;
    if (env.VITE_HOST) host = true;
  } catch (e) {
    proxyUrl = "http://localhost:8000";
  }
  console.log(`Proxy url ${proxyUrl}, host: ${host}`);
  return defineConfig({
    plugins: [vue()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      host: host,
      proxy: {
        "/api": proxyUrl,
      },
    },
  });
};
