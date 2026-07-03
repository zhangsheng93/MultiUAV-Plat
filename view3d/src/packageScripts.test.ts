import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

type PackageJson = {
  scripts: Record<string, string>;
};

const packageJson = JSON.parse(readFileSync('package.json', 'utf8')) as PackageJson;

test('npm run dev tries backend by default while demo mode is explicit', () => {
  assert.equal(packageJson.scripts.dev, 'VITE_VIEWER_DATA_SOURCE=backend vite --host 127.0.0.1 --port 5173');
  assert.equal(packageJson.scripts['dev:backend'], 'VITE_VIEWER_DATA_SOURCE=backend vite --host 127.0.0.1 --port 5173');
  assert.equal(packageJson.scripts['dev:demo'], 'VITE_VIEWER_DATA_SOURCE=demo vite --host 127.0.0.1 --port 5173');
});
