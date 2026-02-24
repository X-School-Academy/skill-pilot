import { build } from "esbuild";
import dotenv from "dotenv";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const distDir = path.join(rootDir, "dist");

dotenv.config({ path: path.join(rootDir, ".env") });

const socketServerUrl = process.env.SOCKET_SERVER_URL || "http://127.0.0.1:3001";
const localChromeToken = process.env.LOCAL_CHROME_TOKEN || "";

async function copyStaticFiles() {
  const staticFiles = ["manifest.json", "popup.html", "popup.css", "popup.js"];

  await fs.rm(distDir, { recursive: true, force: true });
  await fs.mkdir(distDir, { recursive: true });

  for (const file of staticFiles) {
    await fs.copyFile(path.join(rootDir, file), path.join(distDir, file));
  }
}

async function bundleBackground() {
  await build({
    entryPoints: [path.join(rootDir, "src/background.js")],
    outfile: path.join(distDir, "background.js"),
    bundle: true,
    format: "iife",
    platform: "browser",
    target: ["chrome114"],
    sourcemap: false,
    minify: false,
    define: {
      "process.env.SOCKET_SERVER_URL": JSON.stringify(socketServerUrl),
      "process.env.LOCAL_CHROME_TOKEN": JSON.stringify(localChromeToken)
    }
  });
}

await copyStaticFiles();
await bundleBackground();

console.log("Build complete: chrome-extension/dist");
