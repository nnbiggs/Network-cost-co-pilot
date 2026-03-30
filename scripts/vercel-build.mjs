/**
 * Vercel build: emit static landing page + copy logo.
 * Set STREAMLIT_APP_URL in Vercel → Project → Environment Variables.
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");
const out = path.join(root, "out");
const url =
  process.env.STREAMLIT_APP_URL?.trim() ||
  "https://YOUR-APP-NAME.streamlit.app";

const templatePath = path.join(root, "index.template.html");
let html = fs.readFileSync(templatePath, "utf8");
html = html.replace(/__STREAMLIT_APP_URL__/g, url);

fs.mkdirSync(out, { recursive: true });
fs.writeFileSync(path.join(out, "index.html"), html, "utf8");

const logoSrc = path.join(root, "assets", "pwc_logo.svg");
const logoDest = path.join(out, "assets", "pwc_logo.svg");
if (fs.existsSync(logoSrc)) {
  fs.mkdirSync(path.dirname(logoDest), { recursive: true });
  fs.copyFileSync(logoSrc, logoDest);
}

console.log("Built out/index.html → launch URL:", url);
