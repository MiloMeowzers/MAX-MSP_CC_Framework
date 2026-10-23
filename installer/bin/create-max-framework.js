#!/usr/bin/env node

'use strict';

const { spawn, execSync, execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const https = require('https');

// The release workflow stamps package.json from the tag before publishing.
const VERSION = require('../package.json').version;
const RELEASE_URL = 'https://github.com/taylorbrook/MAX-MSP_CC_Framework/releases/latest/download/framework.tar.gz';
const MAX_REDIRECTS = 5;

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

const args = process.argv.slice(2);

if (args.includes('--version') || args.includes('-v')) {
  console.log(`create-max-framework v${VERSION}`);
  process.exit(0);
}

if (args.includes('--check-deps')) {
  process.exit(checkDeps() ? 0 : 1);
}

if (args.includes('--help') || args.includes('-h') || args.length === 0) {
  printUsage();
  process.exit(args.length === 0 ? 1 : 0);
}

const projectName = args[0];

if (projectName.startsWith('-')) {
  console.error(`Error: Unknown flag "${projectName}".`);
  printUsage();
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

const targetDir = path.resolve(projectName);

if (fs.existsSync(targetDir)) {
  console.error(`Error: Directory '${projectName}' already exists.`);
  process.exit(1);
}

console.log(`\nCreating MAX/MSP Claude Code Framework in ${projectName}...\n`);

fs.mkdirSync(targetDir, { recursive: true });

downloadAndExtract(RELEASE_URL, targetDir)
  .then(() => {
    // Create the patches directory. No active-project pointer is written: a fresh install has no active project until /max-new or /max-switch sets one.
    const patchesDir = path.join(targetDir, 'patches');
    if (!fs.existsSync(patchesDir)) {
      fs.mkdirSync(patchesDir, { recursive: true });
    }

    // Initialize git repo
    try {
      execSync('git init', { cwd: targetDir, stdio: 'ignore' });
    } catch (_) {
      // git not available -- checkDeps() warns
    }

    // Check Python, its packages and git (warnings only)
    checkDeps();

    // Success message
    console.log(`Done! Your MAX/MSP Claude Code Framework project is ready.\n`);
    console.log(`Next steps:`);
    console.log(`  cd ${projectName}`);
    console.log(`  claude`);
    console.log(`  /max-new my-first-patch\n`);
    console.log(`Prerequisites:`);
    console.log(`  - Claude Code (https://docs.anthropic.com/en/docs/claude-code)`);
    console.log(`  - MAX 9 (https://cycling74.com/products/max)`);
    console.log(`  - Python 3.10+ (for the validation engine)\n`);
  })
  .catch((err) => {
    console.error(`\nError: ${err.message || err}`);
    // Clean up partial directory
    try {
      fs.rmSync(targetDir, { recursive: true, force: true });
    } catch (_) {
      // best effort cleanup
    }
    process.exit(1);
  });

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function printUsage() {
  console.log(`
Usage: npx create-max-framework <project-name>

Create a new MAX/MSP Claude Code Framework project.

Options:
  -h, --help      Show this help message
  -v, --version   Show version number
  --check-deps    Only check Python 3.10+, its packages and git

Examples:
  npx create-max-framework my-synth
  npx create-max-framework granular-sampler
`);
}

/**
 * Download a URL, following up to MAX_REDIRECTS redirects,
 * and pipe the response into tar to extract into targetDir.
 */
function downloadAndExtract(url, dir) {
  return new Promise((resolve, reject) => {
    followRedirects(url, 0, (err, response) => {
      if (err) return reject(err);

      if (response.statusCode !== 200) {
        response.resume(); // consume response to free memory
        return reject(new Error(`Download failed with status ${response.statusCode}`));
      }

      const tar = spawn('tar', ['xz', '--strip-components=1', '-C', dir], {
        stdio: ['pipe', 'inherit', 'pipe']
      });

      let tarStderr = '';
      tar.stderr.on('data', (chunk) => { tarStderr += chunk.toString(); });

      tar.on('close', (code) => {
        if (code !== 0) {
          return reject(new Error(`tar extraction failed (exit ${code}): ${tarStderr.trim()}`));
        }
        resolve();
      });

      tar.on('error', (spawnErr) => {
        reject(new Error(`Failed to spawn tar: ${spawnErr.message}`));
      });

      response.pipe(tar.stdin);

      response.on('error', (dlErr) => {
        tar.kill();
        reject(new Error(`Download error: ${dlErr.message}`));
      });
    });
  });
}

/**
 * Follow HTTP(S) redirects up to maxRedirects.
 */
function followRedirects(url, count, callback) {
  if (count >= MAX_REDIRECTS) {
    return callback(new Error('Too many redirects'));
  }

  const protocol = url.startsWith('https') ? https : require('http');

  protocol.get(url, (response) => {
    const status = response.statusCode;

    if (status === 301 || status === 302 || status === 303 || status === 307 || status === 308) {
      const location = response.headers.location;
      if (!location) {
        return callback(new Error('Redirect with no Location header'));
      }
      response.resume(); // discard body
      return followRedirects(location, count + 1, callback);
    }

    callback(null, response);
  }).on('error', (err) => {
    callback(err);
  });
}

// Prints "<major>.<minor> <1 if >= 3.10 else 0> <comma-separated missing modules>".
// Valid on any Python, so an old interpreter still reports its version.
// A function, not a const: --check-deps runs before this line is reached.
function pyProbe() {
  return [
    'import sys',
    'missing = []',
    'for m in ("numpy", "scipy", "pytest"):',
    '    try:',
    '        __import__(m)',
    '    except Exception:',
    '        missing.append(m)',
    'print("%d.%d %d %s" % (sys.version_info[0], sys.version_info[1],',
    '                       int(sys.version_info >= (3, 10)), ",".join(missing)))',
  ].join('\n');
}

function onPath(cmd) {
  try {
    execFileSync(cmd, ['--version'], { stdio: 'ignore' });
    return true;
  } catch (err) {
    return err.code !== 'ENOENT';
  }
}

/**
 * Check for Python 3.10+, the Python packages the DSP simulation, smoke tests
 * and pre-flight gate need (numpy, scipy, pytest), and git (Rule #7
 * auto-commits every save). Warns only; returns false when Python 3.10+ is
 * missing (review IN-06).
 */
function checkDeps() {
  if (!onPath('git')) {
    console.warn('WARNING: git not found. The framework commits every patch save (Rule #7); install git.');
  }
  let info;
  try {
    info = execFileSync('python3', ['-c', pyProbe()], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
  } catch (err) {
    if (err.code === 'ENOENT') {
      console.warn('WARNING: Python 3 not found. The framework requires Python 3.10+ for the validation engine.');
    } else {
      console.warn('WARNING: python3 did not run. The framework requires Python 3.10+ for the validation engine.');
    }
    return false;
  }
  const [version, ok, missing = ''] = info.split(/\s+/);
  let good = true;
  if (ok !== '1') {
    console.warn(`WARNING: Python 3.10+ required. Found Python ${version}`);
    good = false;
  }
  if (missing) {
    console.warn(`WARNING: Python packages missing: ${missing.split(',').join(', ')} (needed by the DSP simulation, smoke tests and the DSP pre-flight gate; validation works without them).`);
    console.warn('  Install them from the project directory: python3 -m pip install -r requirements-dev.txt');
  }
  return good;
}
