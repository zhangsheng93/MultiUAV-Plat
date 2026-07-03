export type ScreenshotFormat = 'png' | 'jpg' | 'svg' | 'pdf' | 'eps';

export function normalizeScreenshotFormat(value: string): ScreenshotFormat {
  const normalized = value.trim().toLowerCase();
  if (normalized === 'jpeg') return 'jpg';
  if (['png', 'jpg', 'svg', 'pdf', 'eps'].includes(normalized)) return normalized as ScreenshotFormat;
  return 'png';
}

export function getRasterMimeType(format: ScreenshotFormat): 'image/png' | 'image/jpeg' {
  return format === 'jpg' || format === 'pdf' ? 'image/jpeg' : 'image/png';
}

export function getScreenshotExtension(format: ScreenshotFormat): string {
  return format;
}

export function getScreenshotMimeType(format: ScreenshotFormat): string {
  if (format === 'svg') return 'image/svg+xml;charset=utf-8';
  if (format === 'pdf') return 'application/pdf';
  if (format === 'eps') return 'application/postscript';
  return getRasterMimeType(format);
}

export function buildRasterSvg(dataUrl: string, width: number, height: number): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><image width="${width}" height="${height}" href="${dataUrl}"/></svg>`;
}

export function buildRasterEps(pixels: Uint8ClampedArray, width: number, height: number): string {
  const hex: string[] = [];
  for (let index = 0; index < pixels.length; index += 4) {
    hex.push(
      pixels[index].toString(16).padStart(2, '0'),
      pixels[index + 1].toString(16).padStart(2, '0'),
      pixels[index + 2].toString(16).padStart(2, '0')
    );
  }
  return [
    '%!PS-Adobe-3.0 EPSF-3.0',
    `%%BoundingBox: 0 0 ${width} ${height}`,
    '%%LanguageLevel: 2',
    `${width} ${height} scale`,
    `${width} ${height} 8`,
    `[${width} 0 0 -${height} 0 ${height}]`,
    `{<${hex.join('')}>}`,
    'false 3 colorimage',
    'showpage',
    '%%EOF'
  ].join('\n');
}

function dataUrlToBytes(dataUrl: string): Uint8Array {
  const base64 = dataUrl.split(',')[1] || '';
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

function writeAscii(value: string): Uint8Array {
  return new TextEncoder().encode(value);
}

function concatBytes(parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const output = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    output.set(part, offset);
    offset += part.length;
  }
  return output;
}

export function buildRasterPdf(jpegDataUrl: string, width: number, height: number): Uint8Array {
  const imageBytes = dataUrlToBytes(jpegDataUrl);
  const objects = [
    '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
    '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
    `3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${width} ${height}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>\nendobj\n`,
    `4 0 obj\n<< /Type /XObject /Subtype /Image /Width ${width} /Height ${height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${imageBytes.length} >>\nstream\n`,
    `5 0 obj\n<< /Length ${`q ${width} 0 0 ${height} 0 0 cm /Im0 Do Q`.length} >>\nstream\nq ${width} 0 0 ${height} 0 0 cm /Im0 Do Q\nendstream\nendobj\n`
  ];

  const parts: Uint8Array[] = [writeAscii('%PDF-1.4\n')];
  const offsets = [0];
  let cursor = parts[0].length;

  for (let index = 0; index < objects.length; index += 1) {
    offsets.push(cursor);
    if (index === 3) {
      const prefix = writeAscii(objects[index]);
      const suffix = writeAscii('\nendstream\nendobj\n');
      parts.push(prefix, imageBytes, suffix);
      cursor += prefix.length + imageBytes.length + suffix.length;
    } else {
      const bytes = writeAscii(objects[index]);
      parts.push(bytes);
      cursor += bytes.length;
    }
  }

  const xrefOffset = cursor;
  const xrefRows = ['xref', `0 ${objects.length + 1}`, '0000000000 65535 f '];
  for (let index = 1; index < offsets.length; index += 1) {
    xrefRows.push(`${String(offsets[index]).padStart(10, '0')} 00000 n `);
  }
  const trailer = [
    ...xrefRows,
    'trailer',
    `<< /Size ${objects.length + 1} /Root 1 0 R >>`,
    'startxref',
    String(xrefOffset),
    '%%EOF'
  ].join('\n');
  parts.push(writeAscii(trailer));
  return concatBytes(parts);
}
