#!/usr/bin/env node
/**
 * Generate version file for cache busting
 * This script runs during build to create a version.json file
 * with timestamp and git commit hash for detecting updates
 */

import { execSync } from 'child_process';
import { writeFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

function getGitCommitHash() {
  try {
    return execSync('git rev-parse --short HEAD').toString().trim();
  } catch (error) {
    console.warn('Git not available, using timestamp only');
    return null;
  }
}

function generateVersion() {
  const timestamp = Date.now();
  const commitHash = getGitCommitHash();
  const buildDate = new Date().toISOString();

  const version = {
    version: commitHash || `build-${timestamp}`,
    timestamp,
    buildDate,
    commitHash,
  };

  // Write to public directory (will be copied to build)
  const publicPath = join(__dirname, '../public/version.json');
  writeFileSync(publicPath, JSON.stringify(version, null, 2));

  console.log('✓ Generated version file:', version);

  return version;
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  generateVersion();
}

export default generateVersion;
