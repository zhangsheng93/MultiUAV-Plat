import assert from 'node:assert/strict';
import test from 'node:test';

import { buildRasterEps, buildRasterSvg, getRasterMimeType, normalizeScreenshotFormat } from './screenshotExport.ts';

test('normalizes supported screenshot formats', () => {
  assert.equal(normalizeScreenshotFormat('jpeg'), 'jpg');
  assert.equal(normalizeScreenshotFormat('PNG'), 'png');
  assert.equal(normalizeScreenshotFormat('pdf'), 'pdf');
});

test('uses raster mime type for WebGL-backed exports', () => {
  assert.equal(getRasterMimeType('jpg'), 'image/jpeg');
  assert.equal(getRasterMimeType('svg'), 'image/png');
  assert.equal(getRasterMimeType('eps'), 'image/png');
});

test('wraps raster image data in SVG', () => {
  const svg = buildRasterSvg('data:image/png;base64,abc', 640, 360);

  assert.match(svg, /^<svg/);
  assert.match(svg, /width="640"/);
  assert.match(svg, /href="data:image\/png;base64,abc"/);
});

test('builds an EPS raster wrapper with the expected bounding box', () => {
  const eps = buildRasterEps(new Uint8ClampedArray([255, 0, 0, 255]), 1, 1);

  assert.match(eps, /^%!PS-Adobe-3.0 EPSF-3.0/);
  assert.match(eps, /%%BoundingBox: 0 0 1 1/);
  assert.match(eps, /ff0000/);
});
