import { config } from "dotenv";
import path from "node:path";

// Secrets live in one repo-root .env; this folder's .env wins if present.
// Neither overrides variables already set in the shell.
config({ path: path.resolve(process.cwd(), ".env"), quiet: true });
config({ path: path.resolve(process.cwd(), "../.env"), quiet: true });
