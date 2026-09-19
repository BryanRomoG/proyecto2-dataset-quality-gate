import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { env } from '../config/env';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../..');

function fromRepoRoot(configured: string): string {
  return path.isAbsolute(configured) ? configured : path.resolve(repoRoot, configured);
}

export function policyPath(): string {
  return fromRepoRoot(env.QUALITY_POLICY_PATH);
}

export function rawImagesDir(): string {
  return fromRepoRoot(env.RAW_IMAGES_DIR);
}
